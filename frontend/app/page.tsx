"use client";

import { useState, useEffect } from "react";

const API_BASE = "http://localhost:8000/api/v1";

export default function AivopDashboard() {
  // Auth state - supports mock user switching for multi-tenancy demonstration!
  const [userId, setUserId] = useState("00000000-0000-4000-a000-000000000001");
  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  
  // New Project Form
  const [projName, setProjName] = useState("");
  const [projUrl, setProjUrl] = useState("");
  
  // Active Project Detail states
  const [projectDetail, setProjectDetail] = useState<any>(null);
  const [results, setResults] = useState<any>({
    verified_facts: [],
    questions: [],
    keywords: [],
    competitors: [],
    content_opportunities: [],
    agent_runs: [],
    qa_report: null,
    business_profile: null,
    competitor_feature_matrix: null,
    gap_analysis: [],
    ai_visibility_score: null,
    recommendation_simulations: [],
    entity_nodes: [],
    entity_relationships: [],
    content_coverage: [],
    extraction_failures: []
  });
  const [latestReport, setLatestReport] = useState<any>(null);
  const [blogs, setBlogs] = useState<any[]>([]);
  const [selectedBlogCount, setSelectedBlogCount] = useState<number>(10);
  const [generatingBlogs, setGeneratingBlogs] = useState<boolean>(false);
  const [expandedFactIds, setExpandedFactIds] = useState<Record<string, boolean>>({});
  const [questionSearch, setQuestionSearch] = useState("");
  const [questionTypeFilter, setQuestionTypeFilter] = useState("all");
  const [keywordSearch, setKeywordSearch] = useState("");
  const [keywordClusterFilter, setKeywordClusterFilter] = useState("all");
  const [selectedGraphNode, setSelectedGraphNode] = useState<string | null>(null);
  
  // Run management
  const [activeRun, setActiveRun] = useState<any>(null);
  const [pollInterval, setPollInterval] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  // Tabs structure inside project view
  const [activeTab, setActiveTab] = useState("overview");

  // Load projects list whenever userId switches
  useEffect(() => {
    fetchProjects();
    setSelectedProjectId(null);
    setProjectDetail(null);
    setResults({ 
      verified_facts: [], 
      questions: [], 
      keywords: [], 
      competitors: [], 
      content_opportunities: [], 
      agent_runs: [],
      qa_report: null,
      business_profile: null,
      competitor_feature_matrix: null,
      gap_analysis: [],
      ai_visibility_score: null,
      recommendation_simulations: [],
      entity_nodes: [],
      entity_relationships: [],
      content_coverage: [],
      extraction_failures: []
    });
    setLatestReport(null);
    setBlogs([]);
    setExpandedFactIds({});
    setActiveRun(null);
    if (pollInterval) {
      clearInterval(pollInterval);
      setPollInterval(null);
    }
  }, [userId]);

  // Poll active run status if running
  useEffect(() => {
    if (activeRun && (activeRun.status === "pending" || activeRun.status === "crawling" || activeRun.status === "extracting" || activeRun.status === "analyzing")) {
      const interval = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/analysis/status/${activeRun.id}`, {
            headers: { "Authorization": `Bearer mock-${userId}` }
          });
          const data = await res.json();
          if (res.ok) {
            setActiveRun(data);
            if (data.status === "completed" || data.status === "failed") {
              clearInterval(interval);
              setPollInterval(null);
              // Refresh details
              if (selectedProjectId) {
                fetchProjectDetails(selectedProjectId);
              }
            }
          }
        } catch (err) {
          console.error(err);
        }
      }, 3000);
      setPollInterval(interval);
      return () => clearInterval(interval);
    }
  }, [activeRun]);

  const fetchProjects = async () => {
    try {
      setErrorMsg("");
      const res = await fetch(`${API_BASE}/projects`, {
        headers: { "Authorization": `Bearer mock-${userId}` }
      });
      const data = await res.json();
      if (res.ok) {
        setProjects(data);
      } else {
        setErrorMsg(data.detail || "Failed to load projects.");
      }
    } catch (err) {
      setErrorMsg("Unable to connect to backend API server. Make sure the FastAPI backend is running.");
    }
  };

  const createProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projName || !projUrl) return;

    try {
      setErrorMsg("");
      const res = await fetch(`${API_BASE}/projects`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer mock-${userId}`
        },
        body: JSON.stringify({ name: projName, website_url: projUrl })
      });
      const data = await res.json();
      if (res.ok) {
        setProjName("");
        setProjUrl("");
        fetchProjects();
        selectProject(data.id);
      } else {
        setErrorMsg(data.detail || "Failed to create project.");
      }
    } catch (err) {
      setErrorMsg("Error creating project.");
    }
  };

  const selectProject = (id: string) => {
    setSelectedProjectId(id);
    fetchProjectDetails(id);
  };

  const fetchBlogs = async (projectId: string) => {
    try {
      const res = await fetch(`${API_BASE}/blogs/${projectId}`, {
        headers: { "Authorization": `Bearer mock-${userId}` }
      });
      const data = await res.json();
      if (res.ok) {
        setBlogs(data);
      }
    } catch (err) {
      console.error("Error fetching blogs:", err);
    }
  };

  const triggerBlogGeneration = async () => {
    if (!selectedProjectId) return;
    setGeneratingBlogs(true);
    setErrorMsg("");
    try {
      const res = await fetch(`${API_BASE}/blogs/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer mock-${userId}`
        },
        body: JSON.stringify({ project_id: selectedProjectId, count: selectedBlogCount })
      });
      const data = await res.json();
      if (res.ok) {
        setBlogs(data);
      } else {
        setErrorMsg(data.detail || "Failed to generate blogs.");
      }
    } catch (err) {
      setErrorMsg("Error generating blogs.");
    } finally {
      setGeneratingBlogs(false);
    }
  };

  const fetchProjectDetails = async (projectId: string) => {
    setLoading(true);
    setErrorMsg("");
    try {
      // 1. Fetch project profile info
      const projRes = await fetch(`${API_BASE}/projects/${projectId}`, {
        headers: { "Authorization": `Bearer mock-${userId}` }
      });
      if (projRes.ok) {
        const projData = await projRes.json();
        setProjectDetail(projData);
      }

      // 2. Fetch run results (Facts, keywords, etc.)
      const resRes = await fetch(`${API_BASE}/analysis/results/${projectId}`, {
        headers: { "Authorization": `Bearer mock-${userId}` }
      });
      if (resRes.ok) {
        const resData = await resRes.json();
        setResults(resData);
      }

      // 3. Fetch latest report
      const repRes = await fetch(`${API_BASE}/reports/${projectId}/latest`, {
        headers: { "Authorization": `Bearer mock-${userId}` }
      });
      if (repRes.ok) {
        const repData = await repRes.json();
        setLatestReport(repData);
      } else {
        setLatestReport(null);
      }

      // 4. Fetch blogs
      await fetchBlogs(projectId);
      setExpandedFactIds({});
    } catch (err) {
      setErrorMsg("Error loading project details.");
    } finally {
      setLoading(false);
    }
  };

  const triggerAnalysisRun = async () => {
    if (!selectedProjectId) return;
    setErrorMsg("");
    try {
      const res = await fetch(`${API_BASE}/analysis/run/${selectedProjectId}`, {
        method: "POST",
        headers: { "Authorization": `Bearer mock-${userId}` }
      });
      const data = await res.json();
      if (res.ok) {
        setActiveRun(data);
      } else {
        setErrorMsg(data.detail || "Failed to run analysis.");
      }
    } catch (err) {
      setErrorMsg("Error starting analysis.");
    }
  };

  const deleteProject = async (id: string) => {
    if (!confirm("Are you sure you want to delete this project?")) return;
    try {
      const res = await fetch(`${API_BASE}/projects/${id}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer mock-${userId}` }
      });
      if (res.ok) {
        setProjects(projects.filter(p => p.id !== id));
        if (selectedProjectId === id) {
          setSelectedProjectId(null);
          setProjectDetail(null);
        }
      }
    } catch (err) {
      setErrorMsg("Error deleting project.");
    }
  };

  const downloadReportRaw = async (format: string) => {
    if (!latestReport) return;
    try {
      const res = await fetch(`${API_BASE}/reports/download/${latestReport.id}/${format}`, {
        headers: { "Authorization": `Bearer mock-${userId}` }
      });
      
      if (format === "json") {
        const data = await res.json();
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data, null, 2));
        const downloadAnchor = document.createElement("a");
        downloadAnchor.setAttribute("href", dataStr);
        downloadAnchor.setAttribute("download", `aivop_report_${selectedProjectId}.json`);
        document.body.appendChild(downloadAnchor);
        downloadAnchor.click();
        downloadAnchor.remove();
      } else {
        const data = await res.text();
        const dataStr = "data:text/markdown;charset=utf-8," + encodeURIComponent(data);
        const downloadAnchor = document.createElement("a");
        downloadAnchor.setAttribute("href", dataStr);
        downloadAnchor.setAttribute("download", `aivop_report_${selectedProjectId}.md`);
        document.body.appendChild(downloadAnchor);
        downloadAnchor.click();
        downloadAnchor.remove();
      }
    } catch (err) {
      setErrorMsg("Error downloading report.");
    }
  };

  return (
    <div className="dashboard-layout">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
          </svg>
          <span>AIVOP Dashboard</span>
        </div>

        {/* Multi-Tenancy Demo Switcher */}
        <div className="form-group" style={{ marginBottom: "2rem" }}>
          <label className="form-label">Active Workspace User (RLS Demo)</label>
          <select 
            className="form-input" 
            value={userId} 
            onChange={(e) => setUserId(e.target.value)}
            style={{ padding: "0.5rem", borderRadius: "8px", background: "rgba(255,255,255,0.05)" }}
          >
            <option value="00000000-0000-4000-a000-000000000001">Preetham (User 1)</option>
            <option value="00000000-0000-4000-a000-000000000002">David Miller (User 2)</option>
            <option value="00000000-0000-4000-a000-000000000003">Sarah Connor (User 3)</option>
          </select>
        </div>

        <h3 className="form-label" style={{ marginBottom: "0.5rem" }}>My Projects ({projects.length})</h3>
        <ul className="sidebar-menu">
          {projects.map((proj) => (
            <li 
              key={proj.id} 
              className={`sidebar-item ${selectedProjectId === proj.id ? "active" : ""}`}
            >
              <a href="#" onClick={() => selectProject(proj.id)} style={{ justifyContent: "space-between" }}>
                <span>{proj.project_name}</span>
                <span onClick={(e) => { e.stopPropagation(); deleteProject(proj.id); }} style={{ opacity: 0.5, cursor: "pointer" }}>×</span>
              </a>
            </li>
          ))}
        </ul>
      </aside>

      {/* Main Panel */}
      <main className="main-content">
        {errorMsg && (
          <div className="card" style={{ borderLeft: "4px solid var(--accent-red)", padding: "1rem", marginBottom: "2rem" }}>
            <p style={{ color: "HSL(0, 100%, 75%)", fontWeight: 600 }}>⚠️ {errorMsg}</p>
          </div>
        )}

        {!selectedProjectId ? (
          <div>
            <h1 className="text-gradient" style={{ fontSize: "2.8rem", marginBottom: "1rem" }}>
              AI Visibility Optimization Platform
            </h1>
            <p style={{ color: "var(--text-muted)", fontSize: "1.1rem", marginBottom: "2.5rem", maxWidth: "800px" }}>
              Help your brand gain organic visibility inside AI Recommendation Systems like ChatGPT, Gemini, and Claude. Crawl website structures, extract verified facts, and generate optimization triggers.
            </p>

            {/* Create Project Card */}
            <div className="card glow-border" style={{ maxWidth: "600px" }}>
              <h2 style={{ marginBottom: "1.5rem" }}>Create New Optimization Project</h2>
              <form onSubmit={createProject}>
                <div className="form-group">
                  <label className="form-label">Project Name</label>
                  <input 
                    type="text" 
                    className="form-input" 
                    placeholder="e.g. Acme SaaS CRM" 
                    value={projName} 
                    onChange={(e) => setProjName(e.target.value)} 
                    required 
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Company Website URL</label>
                  <input 
                    type="url" 
                    className="form-input" 
                    placeholder="e.g. https://acme-crm.com" 
                    value={projUrl} 
                    onChange={(e) => setProjUrl(e.target.value)} 
                    required 
                  />
                </div>
                <button type="submit" className="btn btn-primary" style={{ width: "100%", marginTop: "1rem" }}>
                  Create Project & Start
                </button>
              </form>
            </div>
          </div>
        ) : (
          <div>
            {/* Project Hub Header */}
            {projectDetail && (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2rem" }}>
                <div>
                  <h1 className="text-gradient" style={{ fontSize: "2.4rem" }}>{projectDetail.project_name}</h1>
                  <p style={{ color: "var(--text-muted)" }}>
                    🌐 Target Website: <a href={projectDetail.website_url} target="_blank" rel="noreferrer" style={{ color: "var(--secondary)" }}>{projectDetail.website_url}</a>
                    {projectDetail.industry && <span className="badge badge-info" style={{ marginLeft: "1rem" }}>{projectDetail.industry}</span>}
                  </p>
                </div>
                <div style={{ display: "flex", gap: "1rem" }}>
                  <button 
                    className={`btn ${activeRun ? "btn-secondary" : "btn-primary"}`} 
                    onClick={triggerAnalysisRun}
                    disabled={!!(activeRun && ["pending", "crawling", "extracting", "analyzing"].includes(activeRun.status))}
                  >
                    {activeRun && ["pending", "crawling", "extracting", "analyzing"].includes(activeRun.status) ? (
                      <>
                        <div className="spinner"></div>
                        <span>Processing ({activeRun.status})...</span>
                      </>
                    ) : (
                      <span>Run AI Crawler & Agents</span>
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* Run Progress Banner */}
            {activeRun && (
              <div className="card" style={{ marginBottom: "2rem", background: "rgba(110, 0, 255, 0.05)", border: "1px solid var(--primary)" }}>
                <h3>Active Intelligence Execution Run</h3>
                <p style={{ color: "var(--text-muted)", margin: "0.25rem 0 1rem 0" }}>
                  Run ID: {activeRun.id} | Started: {new Date(activeRun.started_at).toLocaleTimeString()}
                </p>
                <div style={{ display: "flex", gap: "1.5rem", alignItems: "center" }}>
                  <span className={`badge ${
                    activeRun.status === "completed" ? "badge-success" : 
                    activeRun.status === "failed" ? "badge-danger" : "badge-warning"
                  }`}>
                    Status: {activeRun.status}
                  </span>
                  {activeRun.error_message && <span style={{ color: "var(--accent-red)" }}>Error: {activeRun.error_message}</span>}
                </div>
              </div>
            )}

            {/* Core Stats Overview */}
            <div className="grid-3" style={{ marginBottom: "2.5rem" }}>
              <div className="metric-card">
                <div>
                  <div className="metric-title">Verified Facts Extracted</div>
                  <div className="metric-value">{results.verified_facts.length}</div>
                </div>
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--accent-green)" strokeWidth="2">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
              </div>
              <div className="metric-card">
                <div>
                  <div className="metric-title">LLM Queries Discovered</div>
                  <div className="metric-value">{results.questions.length}</div>
                </div>
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--secondary)" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
              </div>
              <div className="metric-card">
                <div>
                  <div className="metric-title">Semantic Keyword Clusters</div>
                  <div className="metric-value">{results.keywords.length}</div>
                </div>
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2">
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                  <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
                  <line x1="12" y1="22.08" x2="12" y2="12" />
                </svg>
              </div>
            </div>

            {/* Tabs Navigation */}
            <div className="tabs-bar" style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
              <button className={`tab-btn ${activeTab === "overview" ? "active" : ""}`} onClick={() => setActiveTab("overview")}>Overview</button>
              <button className={`tab-btn ${activeTab === "bi" ? "active" : ""}`} onClick={() => setActiveTab("bi")}>Business Intelligence</button>
              <button className={`tab-btn ${activeTab === "facts" ? "active" : ""}`} onClick={() => setActiveTab("facts")}>Verified Facts</button>
              <button className={`tab-btn ${activeTab === "questions" ? "active" : ""}`} onClick={() => setActiveTab("questions")}>Question Discovery</button>
              <button className={`tab-btn ${activeTab === "keywords" ? "active" : ""}`} onClick={() => setActiveTab("keywords")}>Keyword Intelligence</button>
              <button className={`tab-btn ${activeTab === "competitors" ? "active" : ""}`} onClick={() => setActiveTab("competitors")}>Competitor Analysis</button>
              <button className={`tab-btn ${activeTab === "content" ? "active" : ""}`} onClick={() => setActiveTab("content")}>Content Opportunities</button>
              <button className={`tab-btn ${activeTab === "blogs" ? "active" : ""}`} onClick={() => setActiveTab("blogs")}>Generate Blogs</button>
              <button className={`tab-btn ${activeTab === "reports" ? "active" : ""}`} onClick={() => setActiveTab("reports")}>Reports</button>
              <button className={`tab-btn ${activeTab === "agent_monitor" ? "active" : ""}`} onClick={() => setActiveTab("agent_monitor")}>Agent Monitor</button>
            </div>

            {/* Tab Panels */}
            {activeTab === "overview" && (
              <div>
                {/* Quality Assurance Audit Card */}
                {results.qa_report && (
                  <div className="card glow-border" style={{ marginBottom: "2rem", borderLeft: results.qa_report.approval_status === "approved" ? "4px solid var(--accent-green)" : "4px solid var(--accent-red)", background: "rgba(255,255,255,0.02)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem", marginBottom: "1.5rem" }}>
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "0.25rem" }}>
                          <h2 style={{ fontSize: "1.5rem", margin: 0 }}>Quality Assurance Audit</h2>
                          <span className={`badge ${results.qa_report.approval_status === "approved" ? "badge-success" : "badge-danger"}`} style={{ fontSize: "0.85rem", padding: "0.35rem 0.85rem" }}>
                            {results.qa_report.approval_status === "approved" ? "✓ Approved" : "⚠️ Flagged"}
                          </span>
                        </div>
                        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
                          Programmatic and semantic checks to verify optimization intelligence reliability.
                        </p>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", fontWeight: 600 }}>QA Health Score</div>
                        <div style={{ fontSize: "2.2rem", fontWeight: 800, color: results.qa_report.qa_score >= 80 ? "var(--accent-green)" : results.qa_report.qa_score >= 70 ? "var(--accent-amber)" : "var(--accent-red)" }}>
                          {results.qa_report.qa_score.toFixed(0)}/100
                        </div>
                      </div>
                    </div>

                    <div className="grid-3" style={{ gap: "1rem", marginBottom: "1.5rem" }}>
                      <div style={{ background: "rgba(255, 255, 255, 0.03)", padding: "1rem", borderRadius: "12px", border: "1px solid var(--border-color)" }}>
                        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 600 }}>Duplicate Facts</div>
                        <div style={{ fontSize: "1.6rem", fontWeight: 700, marginTop: "0.25rem", color: results.qa_report.checks?.duplicate_facts_count === 0 ? "var(--accent-green)" : "var(--accent-amber)" }}>
                          {results.qa_report.checks?.duplicate_facts_count ?? 0}
                        </div>
                      </div>
                      <div style={{ background: "rgba(255, 255, 255, 0.03)", padding: "1rem", borderRadius: "12px", border: "1px solid var(--border-color)" }}>
                        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 600 }}>Missing Evidence</div>
                        <div style={{ fontSize: "1.6rem", fontWeight: 700, marginTop: "0.25rem", color: results.qa_report.checks?.missing_evidence_count === 0 ? "var(--accent-green)" : "var(--accent-red)" }}>
                          {results.qa_report.checks?.missing_evidence_count ?? 0}
                        </div>
                      </div>
                      <div style={{ background: "rgba(255, 255, 255, 0.03)", padding: "1rem", borderRadius: "12px", border: "1px solid var(--border-color)" }}>
                        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 600 }}>Low Confidence Facts</div>
                        <div style={{ fontSize: "1.6rem", fontWeight: 700, marginTop: "0.25rem", color: results.qa_report.checks?.low_confidence_facts_count === 0 ? "var(--accent-green)" : "var(--accent-amber)" }}>
                          {results.qa_report.checks?.low_confidence_facts_count ?? 0}
                        </div>
                      </div>
                    </div>

                    {results.qa_report.checks?.unsupported_claims && results.qa_report.checks.unsupported_claims.length > 0 && (
                      <div style={{ borderTop: "1px solid var(--border-color)", paddingTop: "1.25rem" }}>
                        <h4 style={{ color: "var(--accent-red)", marginBottom: "0.5rem", fontSize: "0.95rem" }}>⚠️ Unsupported claims detected (potential hallucinations):</h4>
                        <ul style={{ paddingLeft: "1.25rem", fontSize: "0.9rem", color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: "0.35rem" }}>
                          {results.qa_report.checks.unsupported_claims.map((claim: string, idx: number) => (
                            <li key={idx}>{claim}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* AI Visibility Scoring Engine Widget */}
                {results.ai_visibility_score && (
                  <div className="card glow-border" style={{ marginBottom: "2rem", background: "linear-gradient(135deg, rgba(110,0,255,0.05) 0%, rgba(0,255,136,0.02) 100%)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
                      <div>
                        <h2 style={{ fontSize: "1.6rem", margin: 0 }}>AI Visibility Readiness Index</h2>
                        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>Calculated based on search queries, content completeness, structured schema and trust metrics.</p>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <span style={{ fontSize: "3rem", fontWeight: 800, color: "var(--secondary)" }}>
                          {results.ai_visibility_score.overall_score}/100
                        </span>
                      </div>
                    </div>

                    <h3 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>Engine Sub-Scores</h3>
                    <div className="grid-3" style={{ gap: "1rem", marginBottom: "1.5rem" }}>
                      {Object.entries(results.ai_visibility_score.sub_scores || {}).map(([key, val]: any) => (
                        <div key={key} style={{ background: "rgba(255,255,255,0.03)", padding: "0.75rem 1rem", borderRadius: "10px", border: "1px solid var(--border-color)" }}>
                          <div style={{ textTransform: "capitalize", fontSize: "0.8rem", color: "var(--text-muted)" }}>{key.replace("_", " ")}</div>
                          <div style={{ fontSize: "1.3rem", fontWeight: 700, marginTop: "0.25rem", color: val >= 70 ? "var(--accent-green)" : val >= 50 ? "var(--accent-amber)" : "var(--accent-red)" }}>{val}%</div>
                        </div>
                      ))}
                    </div>

                    <div style={{ borderTop: "1px solid var(--border-color)", paddingTop: "1rem" }}>
                      <h4 style={{ color: "var(--secondary)", fontSize: "0.95rem", marginBottom: "0.5rem" }}>Key Recommendations:</h4>
                      <ul style={{ paddingLeft: "1.2rem", fontSize: "0.9rem", color: "var(--text-muted)" }}>
                        {results.ai_visibility_score.recommendations?.map((r: string, idx: number) => <li key={idx} style={{ marginBottom: "0.25rem" }}>• {r}</li>)}
                      </ul>
                    </div>
                  </div>
                )}

                {/* Recommendation Simulation Engine Widget */}
                {results.recommendation_simulations && results.recommendation_simulations.length > 0 && (
                  <div className="card" style={{ marginBottom: "2rem" }}>
                    <h2 style={{ marginBottom: "1rem" }}>AI Recommendation Simulation Engine</h2>
                    <p style={{ color: "var(--text-muted)", fontSize: "0.95rem", marginBottom: "1.5rem" }}>
                      Simulates semantic user search queries inside LLMs (like ChatGPT, Gemini, Perplexity) to verify if the business is organically recommended.
                    </p>
                    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                      {results.recommendation_simulations.map((sim: any, idx: number) => (
                        <div key={idx} className="card glow-border" style={{ padding: "1.25rem", background: "rgba(255,255,255,0.01)" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                            <h3 style={{ margin: 0, fontSize: "1.1rem" }}>&quot;{sim.query}&quot;</h3>
                            <div style={{ textAlign: "right" }}>
                              <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", display: "block" }}>Recommendation Likelihood</span>
                              <strong style={{ fontSize: "1.3rem", color: sim.recommendation_probability >= 70 ? "var(--accent-green)" : sim.recommendation_probability >= 50 ? "var(--accent-amber)" : "var(--accent-red)" }}>
                                {sim.recommendation_probability}%
                              </strong>
                            </div>
                          </div>
                          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", borderLeft: "2px solid var(--border-color)", paddingLeft: "1rem", fontSize: "0.9rem" }}>
                            <div>
                              <strong style={{ color: "var(--accent-green)" }}>✓ Supporting Evidence:</strong>
                              <ul style={{ paddingLeft: "1.2rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                                {sim.supporting_evidence?.map((e: string, i: number) => <li key={i}>{e}</li>)}
                              </ul>
                            </div>
                            <div style={{ marginTop: "0.5rem" }}>
                              <strong style={{ color: "var(--accent-red)" }}>⚠️ Missing Requirements:</strong>
                              <ul style={{ paddingLeft: "1.2rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                                {sim.missing_requirements?.map((m: string, i: number) => <li key={i}>{m}</li>)}
                              </ul>
                            </div>
                            <div style={{ marginTop: "0.5rem" }}>
                              <strong style={{ color: "var(--secondary)" }}>💡 Improvement Actions:</strong>
                              <ul style={{ paddingLeft: "1.2rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                                {sim.improvement_actions?.map((imp: string, i: number) => <li key={i}>{imp}</li>)}
                              </ul>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {latestReport ? (
                  <div className="card">
                    <h2 style={{ marginBottom: "1rem" }}>Executive Summary</h2>
                    <p style={{ lineHeight: 1.6, color: "var(--text-muted)", marginBottom: "2rem" }}>
                      {latestReport.content.executive_summary}
                    </p>

                    <h2 style={{ marginBottom: "1rem" }}>AI Recommendation System Gaps</h2>
                    <p style={{ lineHeight: 1.6, color: "var(--text-muted)", marginBottom: "2rem" }}>
                      {latestReport.content.ai_visibility_analysis}
                    </p>

                    <div className="grid-2">
                      <div className="card" style={{ padding: "1.5rem" }}>
                        <h3 style={{ color: "var(--accent-green)", marginBottom: "0.5rem" }}>SWOT Strengths</h3>
                        <ul>
                           {latestReport.content.swot?.strengths?.map((str: string, i: number) => (
                            <li key={i} style={{ color: "var(--text-muted)", marginBottom: "0.5rem" }}>✓ {str}</li>
                          ))}
                        </ul>
                      </div>
                      <div className="card" style={{ padding: "1.5rem" }}>
                        <h3 style={{ color: "var(--accent-red)", marginBottom: "0.5rem" }}>SWOT Weaknesses</h3>
                        <ul>
                          {latestReport.content.swot?.weaknesses?.map((wk: string, i: number) => (
                            <li key={i} style={{ color: "var(--text-muted)", marginBottom: "0.5rem" }}>⚠️ {wk}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="card flex-center" style={{ flexDirection: "column", padding: "4rem" }}>
                    <p style={{ color: "var(--text-muted)", marginBottom: "1.5rem" }}>No intelligence has been generated yet for this project.</p>
                    <button className="btn btn-primary" onClick={triggerAnalysisRun}>
                      Trigger Initial Analysis Run
                    </button>
                  </div>
                )}
              </div>
            )}

            {activeTab === "bi" && (
              <div>
                {results.business_profile ? (
                  <div>
                    {/* Brand Details Card */}
                    <div className="card glow-border" style={{ marginBottom: "2rem" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "1.5rem", marginBottom: "1.5rem" }}>
                        <div>
                          <h2 style={{ fontSize: "1.8rem", margin: 0 }}>{results.business_profile.company_name}</h2>
                          <span className="badge badge-info" style={{ marginTop: "0.5rem", display: "inline-block" }}>{results.business_profile.industry}</span>
                          <span className="badge badge-success" style={{ marginTop: "0.5rem", marginLeft: "0.5rem", display: "inline-block" }}>{results.business_profile.business_model}</span>
                        </div>
                      </div>

                      <div style={{ display: "flex", flexDirection: "column", gap: "1rem", fontSize: "0.95rem" }}>
                        <p style={{ color: "var(--text-muted)", lineHeight: 1.6 }}><strong>Description:</strong> {results.business_profile.description}</p>
                        <p style={{ color: "var(--text-muted)" }}><strong>Corporate Mission:</strong> {results.business_profile.mission}</p>
                        <p style={{ color: "var(--text-muted)" }}><strong>Corporate Vision:</strong> {results.business_profile.vision}</p>
                        <p style={{ color: "var(--text-muted)" }}><strong>Target Audience:</strong> {results.business_profile.target_audience}</p>
                        <p style={{ color: "var(--text-muted)" }}><strong>Unique Selling Proposition (USP):</strong> <strong style={{ color: "var(--secondary)" }}>{results.business_profile.usp}</strong></p>
                      </div>

                      {/* Trust Signals */}
                      <div style={{ marginTop: "1.5rem", borderTop: "1px solid var(--border-color)", paddingTop: "1.5rem" }}>
                        <h4 style={{ color: "var(--accent-green)", fontSize: "1rem", marginBottom: "0.5rem" }}>Verified Trust Signals & Credentials</h4>
                        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                          {results.business_profile.trust_signals && results.business_profile.trust_signals.length > 0 ? (
                            results.business_profile.trust_signals.map((sig: string, idx: number) => (
                              <span key={idx} className="badge badge-success" style={{ background: "rgba(0, 255, 136, 0.1)", color: "var(--accent-green)" }}>✓ {sig}</span>
                            ))
                          ) : (
                            <span style={{ color: "var(--text-muted)" }}>NOT FOUND</span>
                          )}
                        </div>
                      </div>

                      {/* AI Opportunities */}
                      <div style={{ marginTop: "1.5rem", borderTop: "1px solid var(--border-color)", paddingTop: "1.5rem" }}>
                        <h4 style={{ color: "var(--secondary)", fontSize: "1rem", marginBottom: "0.5rem" }}>AI Visibility Opportunities</h4>
                        <ul style={{ paddingLeft: "1.2rem", fontSize: "0.9rem", color: "var(--text-muted)" }}>
                          {results.business_profile.ai_visibility_opportunities && results.business_profile.ai_visibility_opportunities.length > 0 ? (
                            results.business_profile.ai_visibility_opportunities.map((opp: string, idx: number) => (
                              <li key={idx} style={{ marginBottom: "0.25rem" }}>{opp}</li>
                            ))
                          ) : (
                            <li style={{ color: "var(--text-muted)" }}>NOT FOUND</li>
                          )}
                        </ul>
                      </div>
                    </div>

                    {/* SWOT analysis */}
                    <div className="grid-2" style={{ gap: "2rem", marginBottom: "2rem" }}>
                      <div className="card" style={{ borderLeft: "4px solid var(--accent-green)", background: "rgba(0, 255, 136, 0.02)" }}>
                        <h3 style={{ color: "var(--accent-green)", marginBottom: "0.75rem" }}>Strengths (S)</h3>
                        <ul style={{ paddingLeft: "1.2rem", color: "var(--text-muted)", fontSize: "0.9rem" }}>
                          {results.business_profile.strengths?.map((s: string, idx: number) => <li key={idx} style={{ marginBottom: "0.25rem" }}>✓ {s}</li>)}
                        </ul>
                      </div>
                      <div className="card" style={{ borderLeft: "4px solid var(--accent-red)", background: "rgba(255, 70, 70, 0.02)" }}>
                        <h3 style={{ color: "var(--accent-red)", marginBottom: "0.75rem" }}>Weaknesses (W)</h3>
                        <ul style={{ paddingLeft: "1.2rem", color: "var(--text-muted)", fontSize: "0.9rem" }}>
                          {results.business_profile.weaknesses?.map((w: string, idx: number) => <li key={idx} style={{ marginBottom: "0.25rem" }}>⚠️ {w}</li>)}
                        </ul>
                      </div>
                      <div className="card" style={{ borderLeft: "4px solid var(--accent-amber)", background: "rgba(255, 170, 0, 0.02)" }}>
                        <h3 style={{ color: "var(--accent-amber)", marginBottom: "0.75rem" }}>Opportunities (O)</h3>
                        <ul style={{ paddingLeft: "1.2rem", color: "var(--text-muted)", fontSize: "0.9rem" }}>
                          {results.business_profile.opportunities?.map((o: string, idx: number) => <li key={idx} style={{ marginBottom: "0.25rem" }}>↗ {o}</li>)}
                        </ul>
                      </div>
                      <div className="card" style={{ borderLeft: "4px solid var(--primary)", background: "rgba(110, 0, 255, 0.02)" }}>
                        <h3 style={{ color: "var(--primary)", marginBottom: "0.75rem" }}>Risks (T)</h3>
                        <ul style={{ paddingLeft: "1.2rem", color: "var(--text-muted)", fontSize: "0.9rem" }}>
                          {results.business_profile.risks?.map((r: string, idx: number) => <li key={idx} style={{ marginBottom: "0.25rem" }}>⚡ {r}</li>)}
                        </ul>
                      </div>
                    </div>

                    {/* Knowledge Graph Explorer Widget */}
                    {results.entity_nodes && results.entity_nodes.length > 0 && (
                      <div className="card glow-border" style={{ marginBottom: "2rem" }}>
                        <h2>Knowledge Graph Explorer</h2>
                        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: "1rem" }}>
                          Discovered entities and predicate relationships extracted from crawling the target website. Click an entity to explorer its semantic relationships.
                        </p>
                        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "1.5rem", borderBottom: "1px solid var(--border-color)", paddingBottom: "1rem" }}>
                          {results.entity_nodes.map((node: any) => (
                            <button 
                              key={node.id} 
                              onClick={() => setSelectedGraphNode(selectedGraphNode === node.entity_name ? null : node.entity_name)}
                              className={`btn ${selectedGraphNode === node.entity_name ? "btn-primary" : "btn-secondary"}`}
                              style={{ padding: "0.4rem 0.8rem", fontSize: "0.85rem", borderRadius: "20px" }}
                            >
                              📁 {node.entity_name} ({node.entity_type})
                            </button>
                          ))}
                        </div>

                        {selectedGraphNode ? (
                          <div className="card" style={{ background: "rgba(255,255,255,0.02)", padding: "1rem" }}>
                            <h3 style={{ fontSize: "1.1rem", marginBottom: "0.5rem" }}>Semantic Links for <span style={{ color: "var(--secondary)" }}>{selectedGraphNode}</span></h3>
                            <div className="table-container">
                              <table className="custom-table" style={{ fontSize: "0.85rem" }}>
                                <thead>
                                  <tr>
                                    <th>Subject Node</th>
                                    <th>Predicate Link</th>
                                    <th>Object Node</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {results.entity_relationships.filter((r: any) => 
                                    r.source_node_id === results.entity_nodes.find((n: any) => n.entity_name === selectedGraphNode)?.id ||
                                    r.target_node_id === results.entity_nodes.find((n: any) => n.entity_name === selectedGraphNode)?.id
                                  ).map((rel: any, idx: number) => {
                                    const srcNode = results.entity_nodes.find((n: any) => n.id === rel.source_node_id);
                                    const tgtNode = results.entity_nodes.find((n: any) => n.id === rel.target_node_id);
                                    return (
                                      <tr key={idx}>
                                        <td style={{ color: srcNode?.entity_name === selectedGraphNode ? "var(--secondary)" : "inherit" }}>{srcNode?.entity_name} ({srcNode?.entity_type})</td>
                                        <td><span className="badge badge-info">{rel.relationship_type}</span></td>
                                        <td style={{ color: tgtNode?.entity_name === selectedGraphNode ? "var(--secondary)" : "inherit" }}>{tgtNode?.entity_name} ({tgtNode?.entity_type})</td>
                                      </tr>
                                    );
                                  })}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        ) : (
                          <div style={{ color: "var(--text-muted)", fontSize: "0.9rem", fontStyle: "italic", textAlign: "center", padding: "1rem" }}>
                            Select an entity node above to visualize its knowledge graph relationships.
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="card flex-center" style={{ padding: "4rem" }}>
                    <p style={{ color: "var(--text-muted)" }}>No business profile loaded. Run crawlers to evaluate SWOT.</p>
                  </div>
                )}
              </div>
            )}

            {activeTab === "facts" && (
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
                    {results.verified_facts.length > 0 ? (
                      results.verified_facts.map((fact: any, i: number) => (
                        <>
                          <tr key={i}>
                            <td><span className="badge badge-info">{fact.fact_type}</span></td>
                            <td>
                              <pre style={{ fontSize: "0.8rem", color: "var(--text-muted)", whiteSpace: "pre-wrap", margin: 0 }}>
                                {JSON.stringify(fact.content, null, 2)}
                              </pre>
                            </td>
                            <td>
                              <strong style={{ color: fact.confidence_score > 0.9 ? "var(--accent-green)" : "var(--accent-amber)" }}>
                                {(fact.confidence_score * 100).toFixed(0)}%
                              </strong>
                            </td>
                            <td>
                              <button 
                                className="btn btn-secondary" 
                                style={{ padding: "0.3rem 0.6rem", fontSize: "0.8rem" }}
                                onClick={() => setExpandedFactIds(prev => ({ ...prev, [fact.id]: !prev[fact.id] }))}
                              >
                                {expandedFactIds[fact.id] ? "Hide Evidence" : "Expand Evidence"}
                              </button>
                            </td>
                          </tr>
                          {expandedFactIds[fact.id] && (
                            <tr key={`exp-${i}`} style={{ background: "rgba(255,255,255,0.02)" }}>
                              <td colSpan={4} style={{ padding: "1.25rem", borderLeft: "4px solid var(--accent-green)" }}>
                                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", fontSize: "0.85rem" }}>
                                  <p style={{ color: "var(--accent-green)", fontStyle: "italic", margin: 0 }}>
                                    <strong>Verbatim Evidence Snippet:</strong> &quot;{fact.evidence}&quot;
                                  </p>
                                  <p style={{ margin: 0 }}>
                                    <strong>Source Page URL:</strong> <a href={fact.source_url} target="_blank" rel="noreferrer" style={{ color: "var(--secondary)" }}>{fact.source_url}</a>
                                  </p>
                                  <p style={{ margin: 0 }}>
                                    <strong>Verification Confidence:</strong> {(fact.confidence_score * 100).toFixed(1)}% | <strong>Status:</strong> Verified by Trust Engine
                                  </p>
                                </div>
                              </td>
                            </tr>
                          )}
                        </>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={4} style={{ textAlign: "center", color: "var(--text-dark)" }}>No facts verified yet. Click &quot;Run AI Crawler &amp; Agents&quot; to start.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {activeTab === "questions" && (
              <div>
                {/* Search / Filters for Questions */}
                <div className="card" style={{ padding: "1rem", marginBottom: "1.5rem", display: "flex", gap: "1rem", flexWrap: "wrap" }}>
                  <div style={{ flex: 1, minWidth: "200px" }}>
                    <input 
                      type="text" 
                      placeholder="Search questions by text..."
                      value={questionSearch} 
                      onChange={(e) => setQuestionSearch(e.target.value)} 
                      className="form-input"
                      style={{ padding: "0.4rem 0.8rem", borderRadius: "6px" }}
                    />
                  </div>
                  <div>
                    <select 
                      value={questionTypeFilter} 
                      onChange={(e) => setQuestionTypeFilter(e.target.value)} 
                      className="form-input" 
                      style={{ padding: "0.4rem 0.8rem", borderRadius: "6px" }}
                    >
                      <option value="all">All Intent Categories</option>
                      <option value="Direct Recommendation Queries">Direct Recommendation</option>
                      <option value="Indirect Recommendation Queries">Indirect Comparison</option>
                      <option value="Problem Queries">Problem</option>
                      <option value="Outcome Queries">Outcome</option>
                      <option value="Solution Queries">Solution</option>
                      <option value="Decision Queries">Decision</option>
                      <option value="Trust Queries">Trust & Security</option>
                      <option value="Urgent Need Queries">Urgent Need</option>
                      <option value="Budget Queries">Budget & Price</option>
                      <option value="Implementation Queries">Implementation</option>
                      <option value="Migration Queries">Migration</option>
                      <option value="Scaling Queries">Scaling</option>
                      <option value="Enterprise Queries">Enterprise</option>
                      <option value="Beginner Queries">Beginner</option>
                      <option value="Expert Queries">Expert</option>
                      <option value="Voice Search Queries">Voice Search</option>
                      <option value="Natural Language Queries">Natural Language</option>
                      <option value="AI Search Queries">AI Search</option>
                      <option value="Location Queries">Location</option>
                      <option value="Commercial Queries">Commercial</option>
                    </select>
                  </div>
                </div>

                <div className="grid-2">
                  {results.questions.length > 0 ? (
                    results.questions
                      .filter((q: any) => {
                        const matchesSearch = q.question_text.toLowerCase().includes(questionSearch.toLowerCase());
                        const matchesType = questionTypeFilter === "all" || q.category === questionTypeFilter;
                        return matchesSearch && matchesType;
                      })
                      .slice(0, 100) // Limit rendering to top 100 for high performance
                      .map((q: any, i: number) => (
                        <div key={i} className="card glow-border" style={{ padding: "1.5rem" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                            <span className="badge badge-success" style={{ fontSize: "0.75rem" }}>{q.category}</span>
                            <span className={`badge ${q.priority === "High" ? "badge-danger" : q.priority === "Medium" ? "badge-warning" : "badge-info"}`} style={{ fontSize: "0.75rem" }}>{q.priority} Priority</span>
                          </div>
                          <h3 style={{ marginBottom: "0.75rem", fontSize: "1.1rem" }}>{q.question_text}</h3>
                          
                          {/* Multi-factor Score Grid */}
                          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "0.5rem", fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "1rem", background: "rgba(255,255,255,0.02)", padding: "0.75rem", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.05)" }}>
                            <div>Recommendation: <strong style={{ color: "var(--accent-green)" }}>{q.recommendation_score ?? 0}/100</strong></div>
                            <div>Commercial Score: <strong style={{ color: "var(--secondary)" }}>{q.commercial_score ?? 0}/100</strong></div>
                            <div>Intent Score: <strong>{q.intent_score ?? 0}/100</strong></div>
                            <div>Priority Score: <strong style={{ color: "var(--accent-amber)" }}>{q.priority_score ?? 0}/100</strong></div>
                            <div>Difficulty: <span style={{ color: q.difficulty_estimate === "Hard" ? "var(--accent-red)" : q.difficulty_estimate === "Medium" ? "var(--accent-amber)" : "var(--accent-green)", fontWeight: 600 }}>{q.difficulty_estimate || "Medium"}</span></div>
                            <div>Opportunity: <span style={{ color: q.opportunity_estimate === "High" ? "var(--accent-green)" : "var(--text-muted)" }}>{q.opportunity_estimate || "Medium"}</span></div>
                            <div>Search Intent: <strong style={{ textTransform: "capitalize" }}>{q.intent || "informational"}</strong></div>
                            <div>Confidence: <strong>{(q.confidence_score * 100).toFixed(0)}%</strong></div>
                          </div>

                          <p style={{ fontSize: "0.9rem", color: "var(--text-muted)", borderLeft: "2px solid var(--secondary)", paddingLeft: "1rem", margin: 0 }}>
                            <strong>Optimized Answer Context:</strong><br />
                            {q.recommended_answer}
                          </p>
                        </div>
                      ))
                  ) : (
                    <div className="card flex-center" style={{ gridColumn: "1 / -1", padding: "4rem" }}>
                      <p style={{ color: "var(--text-muted)" }}>No questions discovered yet.</p>
                    </div>
                  )}
                </div>
                {results.questions.length > 100 && (
                  <div style={{ textAlign: "center", marginTop: "1rem", color: "var(--text-muted)", fontSize: "0.85rem" }}>
                    Showing top 100 queries of {results.questions.length} total generated questions (intent grouped).
                  </div>
                )}
              </div>
            )}

            {activeTab === "keywords" && (
              <div>
                {/* Search / Filters for Keywords */}
                <div className="card" style={{ padding: "1rem", marginBottom: "1.5rem", display: "flex", gap: "1rem", flexWrap: "wrap" }}>
                  <div style={{ flex: 1, minWidth: "200px" }}>
                    <input 
                      type="text" 
                      placeholder="Search keywords by text..."
                      value={keywordSearch} 
                      onChange={(e) => setKeywordSearch(e.target.value)} 
                      className="form-input"
                      style={{ padding: "0.4rem 0.8rem", borderRadius: "6px" }}
                    />
                  </div>
                </div>

                <div className="table-container">
                  <table className="custom-table">
                    <thead>
                      <tr>
                        <th>Keyword Text</th>
                        <th>Category</th>
                        <th>Search Intent</th>
                        <th>Theme Cluster</th>
                        <th>Priority</th>
                        <th>Difficulty</th>
                        <th>Opportunity</th>
                        <th>Source</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.keywords.length > 0 ? (
                        results.keywords
                          .filter((kw: any) => kw.keyword_text.toLowerCase().includes(keywordSearch.toLowerCase()))
                          .slice(0, 100) // Paginate/limit to top 100 for fast UI load
                          .map((kw: any, i: number) => (
                            <tr key={i}>
                              <td><strong>{kw.keyword_text}</strong></td>
                              <td><span className="badge badge-info">{kw.category}</span></td>
                              <td><span className="badge badge-success">{kw.search_intent}</span></td>
                              <td style={{ color: "var(--text-muted)" }}>{kw.clustering_theme || "General"}</td>
                              <td><span className={`badge ${kw.priority === "High" ? "badge-danger" : kw.priority === "Medium" ? "badge-warning" : "badge-info"}`} style={{ fontSize: "0.75rem" }}>{kw.priority}</span></td>
                              <td><span style={{ color: kw.difficulty_estimate === "Hard" ? "var(--accent-red)" : kw.difficulty_estimate === "Medium" ? "var(--accent-amber)" : "var(--accent-green)", fontWeight: 600 }}>{kw.difficulty_estimate || "Medium"}</span></td>
                              <td><span style={{ color: kw.opportunity_estimate === "High" ? "var(--accent-green)" : "var(--text-muted)" }}>{kw.opportunity_estimate || "Medium"}</span></td>
                              <td><span className="badge badge-info" style={{ background: "rgba(110, 0, 255, 0.1)", color: "var(--primary)", fontSize: "0.75rem" }}>{kw.source || "Discovery"}</span></td>
                            </tr>
                          ))
                      ) : (
                        <tr>
                          <td colSpan={8} style={{ textAlign: "center", color: "var(--text-dark)" }}>No keywords generated yet.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
                {results.keywords.length > 100 && (
                  <div style={{ textAlign: "center", marginTop: "1rem", color: "var(--text-muted)", fontSize: "0.85rem" }}>
                    Showing top 100 keywords of {results.keywords.length} total generated keywords.
                  </div>
                )}
              </div>
            )}

            {activeTab === "competitors" && (
              <div>
                {/* Competitors List */}
                <div className="grid-2" style={{ marginBottom: "2.5rem" }}>
                  {results.competitors.length > 0 ? (
                    results.competitors.map((comp: any, i: number) => (
                      <div key={i} className="card glow-border" style={{ position: "relative" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                          <h2 style={{ margin: 0 }}>{comp.name}</h2>
                          <div style={{ display: "flex", gap: "0.5rem" }}>
                            <span className={`badge ${comp.competitor_type === "direct" ? "badge-danger" : "badge-warning"}`}>
                              {comp.competitor_type}
                            </span>
                            <span className="badge badge-info" style={{ fontWeight: 800 }}>
                              {comp.similarity_score}% Similar
                            </span>
                          </div>
                        </div>
                        <p style={{ fontStyle: "italic", fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "0.75rem" }}>
                          Description: {comp.description}
                        </p>
                        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1rem" }}>
                          URL: <a href={comp.website_url} target="_blank" rel="noreferrer" style={{ color: "var(--secondary)" }}>{comp.website_url || "NOT FOUND"}</a>
                        </p>

                        <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem", fontSize: "0.8rem", background: "rgba(255,255,255,0.02)", padding: "0.75rem", borderRadius: "8px", marginBottom: "1rem" }}>
                          <div><strong style={{ color: "var(--secondary)" }}>Reason Selected:</strong> {comp.reason_selected?.join(", ") || "NOT FOUND"}</div>
                          <div><strong>Industry Alignment:</strong> {comp.industry_match}</div>
                          <div><strong>Audience Alignment:</strong> {comp.audience_match}</div>
                          <div><strong>Service Alignment:</strong> {comp.service_match}</div>
                        </div>

                        <div style={{ marginBottom: "1rem" }}>
                          <h4 style={{ color: "var(--accent-green)", fontSize: "0.9rem", marginBottom: "0.25rem" }}>Strengths</h4>
                          <ul style={{ paddingLeft: "1.2rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>
                            {comp.strengths?.map((s: string, idx: number) => <li key={idx}>{s}</li>)}
                          </ul>
                        </div>

                        <div style={{ marginBottom: "1rem" }}>
                          <h4 style={{ color: "var(--accent-red)", fontSize: "0.9rem", marginBottom: "0.25rem" }}>Weaknesses</h4>
                          <ul style={{ paddingLeft: "1.2rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>
                            {comp.weaknesses?.map((w: string, idx: number) => <li key={idx}>{w}</li>)}
                          </ul>
                        </div>

                        <div style={{ marginBottom: "1rem" }}>
                          <h4 style={{ color: "var(--secondary)", fontSize: "0.9rem", marginBottom: "0.25rem" }}>Unique Features</h4>
                          <ul style={{ paddingLeft: "1.2rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>
                            {comp.unique_features?.map((uf: string, idx: number) => <li key={idx}>{uf}</li>)}
                          </ul>
                        </div>

                        <div>
                          <h4 style={{ color: "var(--accent-amber)", fontSize: "0.9rem", marginBottom: "0.25rem" }}>Content Opportunities & Gaps</h4>
                          <ul style={{ paddingLeft: "1.2rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>
                            {comp.market_gaps?.map((g: string, idx: number) => <li key={idx}>{g}</li>)}
                          </ul>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="card flex-center" style={{ gridColumn: "1 / -1", padding: "4rem" }}>
                      <p style={{ color: "var(--text-muted)" }}>No competitors analyzed yet.</p>
                    </div>
                  )}
                </div>

                {/* Feature Comparison Matrix */}
                {results.competitor_feature_matrix && (
                  <div className="card glow-border">
                    <h2>Competitor Feature Comparison Matrix</h2>
                    <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: "1.5rem" }}>
                      Cross-examination of core features between our Client and detected industry competitors.
                    </p>
                    <div className="table-container">
                      <table className="custom-table" style={{ fontSize: "0.9rem" }}>
                        <thead>
                          <tr>
                            <th>Optimization Feature</th>
                            <th style={{ color: "var(--secondary)", fontWeight: "bold" }}>Our Client</th>
                            {results.competitors.slice(0, 5).map((comp: any) => (
                              <th key={comp.id}>{comp.name}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {(results.competitor_feature_matrix.features || []).map((feat: any, idx: number) => (
                            <tr key={idx}>
                              <td><strong>{feat.feature_name}</strong></td>
                              <td style={{ color: "var(--secondary)", fontWeight: "bold" }}>{feat.client_value}</td>
                              {results.competitors.slice(0, 5).map((comp: any) => (
                                <td key={comp.id}>{feat.competitor_values[comp.name] || "NOT_FOUND"}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <div className="grid-2" style={{ gap: "1.5rem", marginTop: "1.5rem", borderTop: "1px solid var(--border-color)", paddingTop: "1.5rem" }}>
                      <div>
                        <h4 style={{ color: "var(--accent-amber)", marginBottom: "0.5rem" }}>Unique Competitor Offerings:</h4>
                        <ul style={{ paddingLeft: "1.2rem", color: "var(--text-muted)", fontSize: "0.85rem" }}>
                          {results.competitor_feature_matrix.unique_competitor_features?.map((uf: string, idx: number) => <li key={idx}>{uf}</li>)}
                        </ul>
                      </div>
                      <div>
                        <h4 style={{ color: "var(--accent-red)", marginBottom: "0.5rem" }}>Missing Client Features (Gaps):</h4>
                        <ul style={{ paddingLeft: "1.2rem", color: "var(--text-muted)", fontSize: "0.85rem" }}>
                          {results.competitor_feature_matrix.missing_client_features?.map((mf: string, idx: number) => <li key={idx}>{mf}</li>)}
                        </ul>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === "content" && (
              <div>
                {/* Content Coverage Dashboard */}
                {results.content_coverage && results.content_coverage.length > 0 && (
                  <div className="card glow-border" style={{ marginBottom: "2.5rem" }}>
                    <h2>Content Coverage Dashboard</h2>
                    <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: "1.5rem" }}>
                      Assesses topical completeness of crawled website content compared to target business topics.
                    </p>
                    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                      {results.content_coverage.map((cov: any, idx: number) => (
                        <div key={idx} style={{ background: "rgba(255,255,255,0.01)", border: "1px solid var(--border-color)", padding: "1.25rem", borderRadius: "10px" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                            <h3 style={{ margin: 0 }}>{cov.topic_name}</h3>
                            <strong style={{ fontSize: "1.4rem", color: cov.coverage_score >= 85 ? "var(--accent-green)" : cov.coverage_score >= 70 ? "var(--accent-amber)" : "var(--accent-red)" }}>
                              {cov.coverage_score}% Coverage
                            </strong>
                          </div>
                          <div style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1rem" }}>
                            Content Depth: <span className="badge badge-info">{cov.content_depth}</span>
                          </div>
                          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", fontSize: "0.85rem" }}>
                            <div><strong>Covered Questions:</strong> {cov.question_coverage?.join(", ") || "None"}</div>
                            <div><strong>Covered Keywords:</strong> {cov.keyword_coverage?.join(", ") || "None"}</div>
                            <div><strong>FAQ Points Covered:</strong> {cov.faq_coverage?.join(", ") || "None"}</div>
                            <div style={{ marginTop: "0.5rem", color: "var(--accent-red)" }}><strong>Missing Areas:</strong> {cov.missing_content_areas?.join(", ") || "None"}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Gap Analysis Prioritization Widget */}
                {results.gap_analysis && results.gap_analysis.length > 0 && (
                  <div className="card" style={{ marginBottom: "2.5rem" }}>
                    <h2>GEO Gap Prioritization Matrix</h2>
                    <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: "1.5rem" }}>
                      Prioritized gaps in pages, schemas, and reviews that are preventing recommendations.
                    </p>
                    <div className="table-container">
                      <table className="custom-table" style={{ fontSize: "0.9rem" }}>
                        <thead>
                          <tr>
                            <th>Actionable Gap</th>
                            <th>Priority</th>
                            <th>Improvement Recommendation</th>
                          </tr>
                        </thead>
                        <tbody>
                          {results.gap_analysis.map((gap: any, i: number) => (
                            <tr key={i}>
                              <td><strong>{gap.gap_type}</strong></td>
                              <td>
                                <span className={`badge ${
                                  gap.priority === "high" ? "badge-danger" : 
                                  gap.priority === "medium" ? "badge-warning" : "badge-info"
                                }`}>
                                  {gap.priority.toUpperCase()}
                                </span>
                              </td>
                              <td style={{ color: "var(--text-muted)" }}>{gap.recommendation}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Content opportunities cards */}
                <h2>Scored Content Recommendations</h2>
                <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: "1.5rem" }}>
                  Actionable page creation recommendations scored on effort vs visibility impact.
                </p>
                <div className="grid-2">
                  {results.content_opportunities && results.content_opportunities.length > 0 ? (
                    results.content_opportunities.map((opp: any, i: number) => (
                      <div key={i} className="card glow-border" style={{ padding: "1.5rem" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                          <span className={`badge ${
                            opp.priority === "high" ? "badge-danger" : 
                            opp.priority === "medium" ? "badge-warning" : "badge-info"
                          }`}>
                            {opp.priority.toUpperCase()} Priority
                          </span>
                          <span className="badge badge-success">{opp.content_type}</span>
                        </div>
                        <h3 style={{ marginBottom: "0.75rem", fontSize: "1.2rem" }}>{opp.title}</h3>
                        
                        <div className="grid-2" style={{ gap: "0.75rem", background: "rgba(255,255,255,0.02)", padding: "0.5rem", borderRadius: "6px", fontSize: "0.85rem", marginBottom: "1rem" }}>
                          <div>Impact score: <strong style={{ color: "var(--accent-green)" }}>{opp.impact_score}/100</strong></div>
                          <div>Complexity/Effort: <strong style={{ color: "var(--accent-amber)" }}>{opp.effort_score}/100</strong></div>
                        </div>

                        <div style={{ fontSize: "0.85rem", display: "flex", flexDirection: "column", gap: "0.4rem", color: "var(--text-muted)" }}>
                          <p style={{ margin: 0 }}><strong>GEO Rationale:</strong> {opp.reason}</p>
                          <p style={{ margin: 0 }}><strong>Expected Benefit:</strong> {opp.expected_benefit}</p>
                          <p style={{ margin: 0, color: "var(--accent-green)" }}><strong>Supporting Evidence:</strong> &quot;{opp.supporting_evidence}&quot;</p>
                          <p style={{ margin: 0 }}><strong>Target Keywords:</strong> {opp.related_keywords?.join(", ") || "None"}</p>
                          <p style={{ margin: 0 }}><strong>Target Questions:</strong> {opp.related_questions?.join(", ") || "None"}</p>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="card flex-center" style={{ gridColumn: "1 / -1", padding: "4rem" }}>
                      <p style={{ color: "var(--text-muted)" }}>No content opportunities identified yet. Run agents to audit.</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === "blogs" && (
              <div>
                <div className="card glow-border" style={{ marginBottom: "2.5rem" }}>
                  <h2>Interactive Blog Generation Flow</h2>
                  <p style={{ color: "var(--text-muted)", margin: "0.5rem 0 2rem 0", fontSize: "0.95rem" }}>
                    Select how many blogs you would like to generate based on verified factual assets, and trigger on-demand generation.
                  </p>
                  
                  <div style={{ display: "flex", alignItems: "center", gap: "2rem", flexWrap: "wrap", marginBottom: "1.5rem" }}>
                    <div style={{ display: "flex", gap: "1rem" }}>
                      {[10, 50, 100].map((num) => (
                        <label key={num} style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem", cursor: "pointer", color: "var(--text-muted)" }}>
                          <input 
                            type="radio" 
                            name="blogCount" 
                            value={num} 
                            checked={selectedBlogCount === num} 
                            onChange={() => setSelectedBlogCount(num)} 
                            style={{ accentColor: "var(--secondary)" }}
                          />
                          <span>Generate {num} Blogs</span>
                        </label>
                      ))}
                    </div>

                    <button 
                      className="btn btn-primary" 
                      onClick={triggerBlogGeneration} 
                      disabled={generatingBlogs}
                    >
                      {generatingBlogs ? (
                        <>
                          <div className="spinner"></div>
                          <span>Generating stubs...</span>
                        </>
                      ) : (
                        <span>Generate Blogs</span>
                      )}
                    </button>
                  </div>

                  {generatingBlogs && (
                    <p style={{ fontSize: "0.85rem", color: "var(--accent-amber)" }}>
                      ⏳ Assembling factual references and drafting semantic headlines. This may take up to 10 seconds.
                    </p>
                  )}
                </div>

                <h2>Drafted Blog Publications ({blogs.length})</h2>
                <div className="grid-2">
                  {blogs.length > 0 ? (
                    blogs.map((blog: any, i: number) => (
                      <div key={i} className="card glow-border" style={{ padding: "1.5rem" }}>
                        <h3 style={{ fontSize: "1.15rem", marginBottom: "0.5rem", color: "var(--secondary)" }}>{blog.title}</h3>
                        
                        <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                          <div>
                            <strong>Target Keywords:</strong>{" "}
                            {blog.target_keywords?.map((kw: string, idx: number) => (
                              <span key={idx} className="badge badge-info" style={{ marginRight: "0.25rem", fontSize: "0.75rem" }}>{kw}</span>
                            ))}
                          </div>
                          <div>
                            <strong>Draft Summary:</strong> {blog.content}
                          </div>
                          <div style={{ background: "rgba(255,255,255,0.01)", borderLeft: "2px solid var(--border-color)", paddingLeft: "1rem", marginTop: "0.5rem", fontStyle: "italic", fontSize: "0.8rem" }}>
                            <strong>Suggested Headers:</strong><br />
                            {blog.outline}
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="card flex-center" style={{ gridColumn: "1 / -1", padding: "4rem" }}>
                      <p style={{ color: "var(--text-muted)" }}>No blogs generated yet. Select a count above and click &quot;Generate Blogs&quot;.</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === "agent_monitor" && (
              <div>
                <h2>Agent Execution Monitor</h2>
                <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: "1.5rem" }}>
                  Token consumption, latencies, and execution telemetry for all background agents.
                </p>
                <div className="table-container" style={{ marginBottom: "2.5rem" }}>
                  <table className="custom-table">
                    <thead>
                      <tr>
                        <th>Agent Name</th>
                        <th>Execution Status</th>
                        <th>Input Tokens</th>
                        <th>Output Tokens</th>
                        <th>Processing Time</th>
                        <th>Error Message</th>
                        <th>Executed At</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.agent_runs && results.agent_runs.length > 0 ? (
                        results.agent_runs.map((run: any, i: number) => (
                          <tr key={i}>
                            <td><strong>{run.agent_name}</strong></td>
                            <td>
                              <span className={`badge ${
                                run.status === "completed" ? "badge-success" : "badge-danger"
                              }`}>
                                {run.status}
                              </span>
                            </td>
                            <td>{run.input_tokens}</td>
                            <td>{run.output_tokens}</td>
                            <td>{run.processing_time ? `${run.processing_time.toFixed(2)}s` : "-"}</td>
                            <td style={{ color: "var(--accent-red)", fontSize: "0.85rem" }}>{run.error_message || "-"}</td>
                            <td style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                              {new Date(run.created_at).toLocaleString()}
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={7} style={{ textAlign: "center", color: "var(--text-dark)" }}>
                            No agent execution history recorded yet. Click &quot;Run AI Crawler &amp; Agents&quot; to start.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                {/* Root Cause Analysis Debugger */}
                <h2>Root Cause Analysis Failure Log</h2>
                <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: "1.5rem" }}>
                  Debugging dashboard for tracking page crawler timeouts, verified fact audits, and parser exceptions.
                </p>
                <div className="table-container">
                  <table className="custom-table">
                    <thead>
                      <tr>
                        <th>Failed URL</th>
                        <th>Agent</th>
                        <th>Reason for Failure</th>
                        <th>Exception / Details</th>
                        <th>Logged At</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.extraction_failures && results.extraction_failures.length > 0 ? (
                        results.extraction_failures.map((f: any, i: number) => (
                          <tr key={i}>
                            <td style={{ fontSize: "0.8rem" }}><a href={f.page_url} target="_blank" rel="noreferrer" style={{ color: "var(--secondary)" }}>{f.page_url}</a></td>
                            <td><span className="badge badge-info">{f.agent_name}</span></td>
                            <td style={{ color: "var(--accent-amber)", fontWeight: 600 }}>{f.reason}</td>
                            <td style={{ color: "var(--accent-red)", fontSize: "0.8rem" }}>{f.error_message}</td>
                            <td style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{new Date(f.created_at).toLocaleString()}</td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={5} style={{ textAlign: "center", color: "var(--accent-green)", fontWeight: 600 }}>
                            ✓ No extraction or verification failures recorded. Clean execution run!
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {activeTab === "reports" && (
              <div className="card">
                <h2>Export Optimization Reports</h2>
                <p style={{ color: "var(--text-muted)", margin: "0.5rem 0 2rem 0" }}>
                  Download your AI Visibility optimization package in Markdown format (perfect for reading or copying straight to documentation) or JSON format (for third-party system integrations).
                </p>

                {latestReport ? (
                  <div style={{ display: "flex", gap: "1.5rem" }}>
                    <button className="btn btn-primary" onClick={() => downloadReportRaw("markdown")}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: "0.25rem" }}>
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v4M7 10l5 5 5-5M12 15V3"/>
                      </svg>
                      Download Markdown (.md)
                    </button>
                    <button className="btn btn-secondary" onClick={() => downloadReportRaw("json")}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: "0.25rem" }}>
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v4M7 10l5 5 5-5M12 15V3"/>
                      </svg>
                      Download JSON (.json)
                    </button>
                  </div>
                ) : (
                  <p style={{ color: "var(--accent-red)" }}>No report available yet. Please execute an analysis run first.</p>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
