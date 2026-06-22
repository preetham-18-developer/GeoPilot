"use client";

import { useState, useEffect } from "react";
import OverviewTab from "./components/OverviewTab";
import BusinessIntelligenceTab from "./components/BusinessIntelligenceTab";
import VerifiedFactsTab from "./components/VerifiedFactsTab";
import QuestionDiscoveryTab from "./components/QuestionDiscoveryTab";
import KeywordIntelligenceTab from "./components/KeywordIntelligenceTab";
import CompetitorAnalysisTab from "./components/CompetitorAnalysisTab";
import ContentOpportunitiesTab from "./components/ContentOpportunitiesTab";
import GenerateBlogsTab from "./components/GenerateBlogsTab";
import ReportsTab from "./components/ReportsTab";
import AgentMonitorTab from "./components/AgentMonitorTab";
import ValidationTab from "./components/ValidationTab";
import RecommendationIntelligenceTab from "./components/RecommendationIntelligenceTab";
import RealityCheckerTab from "./components/RealityCheckerTab";
import CompetitorBenchmarkTab from "./components/CompetitorBenchmarkTab";
import LongitudinalTrackerTab from "./components/LongitudinalTrackerTab";
import AdvancedAnalyticsTab from "./components/AdvancedAnalyticsTab";

const API_BASE = "http://localhost:8000/api/v1";

const RUNNING_STATUSES = [
  "pending",
  "queued",
  "crawling",
  "extracting",
  "verifying",
  "analyzing",
  "compiling",
];

const PROGRESS_MAP: Record<string, number> = {
  queued: 5,
  crawling: 20,
  extracting: 40,
  verifying: 60,
  analyzing: 80,
  compiling: 95,
};

const ETA_MAP: Record<string, string> = {
  queued: "150s",
  crawling: "120s",
  extracting: "90s",
  verifying: "60s",
  analyzing: "30s",
  compiling: "10s",
};

const EMPTY_RESULTS = {
  verified_facts: [],
  questions_count: 0,
  questions_categories: [],
  keywords_count: 0,
  keywords_categories: [],
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
  extraction_failures: [],
};

export default function AivopDashboard() {
  // Auth / multi-tenancy
  const [userId, setUserId] = useState("00000000-0000-4000-a000-000000000001");
  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);

  // New project form
  const [projName, setProjName] = useState("");
  const [projUrl, setProjUrl] = useState("");

  // Project detail & results
  const [projectDetail, setProjectDetail] = useState<any>(null);
  const [results, setResults] = useState<any>(EMPTY_RESULTS);
  const [latestReport, setLatestReport] = useState<any>(null);
  const [blogs, setBlogs] = useState<any[]>([]);
  const [selectedBlogCount, setSelectedBlogCount] = useState<number>(10);
  const [generatingBlogs, setGeneratingBlogs] = useState<boolean>(false);
  const [expandedFactIds, setExpandedFactIds] = useState<Record<string, boolean>>({});

  // Questions pagination
  const [questionsPage, setQuestionsPage] = useState(1);
  const [questionsData, setQuestionsData] = useState<any[]>([]);
  const [questionsTotalCount, setQuestionsTotalCount] = useState(0);
  const [questionsLoading, setQuestionsLoading] = useState(false);
  const [questionSearch, setQuestionSearch] = useState("");
  const [questionTypeFilter, setQuestionTypeFilter] = useState("All");
  const [questionsSortBy, setQuestionsSortBy] = useState("priority_score");
  const [questionsSortOrder, setQuestionsSortOrder] = useState("desc");

  // Keywords pagination
  const [keywordsPage, setKeywordsPage] = useState(1);
  const [keywordsData, setKeywordsData] = useState<any[]>([]);
  const [keywordsTotalCount, setKeywordsTotalCount] = useState(0);
  const [keywordsLoading, setKeywordsLoading] = useState(false);
  const [keywordSearch, setKeywordSearch] = useState("");
  const [keywordClusterFilter, setKeywordClusterFilter] = useState("All");
  const [keywordsSortBy, setKeywordsSortBy] = useState("keyword");
  const [keywordsSortOrder, setKeywordsSortOrder] = useState("asc");

  // Run management
  const [activeRun, setActiveRun] = useState<any>(null);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  // Active tab
  const [activeTab, setActiveTab] = useState("overview");

  // ─── Effects ──────────────────────────────────────────────────────────────

  // Reset all state when user switches
  useEffect(() => {
    fetchProjects();
    setSelectedProjectId(null);
    setProjectDetail(null);
    setResults(EMPTY_RESULTS);
    setLatestReport(null);
    setBlogs([]);
    setExpandedFactIds({});
    setActiveRun(null);
    setElapsedTime(0);
    setQuestionsPage(1);
    setQuestionsData([]);
    setQuestionsTotalCount(0);
    setQuestionSearch("");
    setQuestionTypeFilter("All");
    setKeywordsPage(1);
    setKeywordsData([]);
    setKeywordsTotalCount(0);
    setKeywordSearch("");
    setKeywordClusterFilter("All");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  // Poll active run while in a running status
  useEffect(() => {
    if (
      activeRun &&
      RUNNING_STATUSES.includes(activeRun.status)
    ) {
      const interval = setInterval(async () => {
        try {
          const res = await fetch(
            `${API_BASE}/analysis/status/${activeRun.id}`,
            { headers: { Authorization: `Bearer mock-${userId}` } }
          );
          const data = await res.json();
          if (res.ok) {
            setActiveRun(data);
            if (["completed", "failed"].includes(data.status)) {
              clearInterval(interval);
              if (selectedProjectId) fetchProjectDetails(selectedProjectId);
            }
          }
        } catch (err) {
          console.error(err);
        }
      }, 3000);
      return () => clearInterval(interval);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeRun?.id, activeRun?.status]);

  // Poll project detail status while running (handles page refresh recovery)
  useEffect(() => {
    let interval: any = null;
    if (
      selectedProjectId &&
      projectDetail &&
      RUNNING_STATUSES.filter((s) => s !== "pending").includes(projectDetail.status)
    ) {
      interval = setInterval(async () => {
        try {
          const projRes = await fetch(
            `${API_BASE}/projects/${selectedProjectId}`,
            { headers: { Authorization: `Bearer mock-${userId}` } }
          );
          if (projRes.ok) {
            const projData = await projRes.json();
            setProjectDetail(projData);
            if (["completed", "failed"].includes(projData.status)) {
              clearInterval(interval);
              fetchProjectDetails(selectedProjectId);
            }
          }
        } catch (err) {
          console.error(err);
        }
      }, 3000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectDetail?.status, selectedProjectId]);

  // Elapsed time counter
  useEffect(() => {
    let timer: any = null;
    const activeStatus = activeRun?.status || projectDetail?.status;
    const isRunning = RUNNING_STATUSES.filter((s) => s !== "pending").includes(activeStatus);
    const startTimestamp = activeRun?.started_at || projectDetail?.created_at;

    if (isRunning && startTimestamp) {
      setElapsedTime(
        Math.max(
          0,
          Math.floor((Date.now() - new Date(startTimestamp).getTime()) / 1000)
        )
      );
      timer = setInterval(() => {
        setElapsedTime(
          Math.max(
            0,
            Math.floor((Date.now() - new Date(startTimestamp).getTime()) / 1000)
          )
        );
      }, 1000);
    } else {
      setElapsedTime(0);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [
    activeRun?.status,
    projectDetail?.status,
    activeRun?.started_at,
    projectDetail?.created_at,
  ]);

  // Fetch questions when tab or filters change
  useEffect(() => {
    if (selectedProjectId && activeTab === "questions") {
      fetchQuestions(
        selectedProjectId,
        questionsPage,
        questionSearch,
        questionTypeFilter,
        questionsSortBy,
        questionsSortOrder
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    selectedProjectId,
    activeTab,
    questionsPage,
    questionSearch,
    questionTypeFilter,
    questionsSortBy,
    questionsSortOrder,
  ]);

  // Fetch keywords when tab or filters change
  useEffect(() => {
    if (selectedProjectId && activeTab === "keywords") {
      fetchKeywords(
        selectedProjectId,
        keywordsPage,
        keywordSearch,
        keywordClusterFilter,
        keywordsSortBy,
        keywordsSortOrder
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    selectedProjectId,
    activeTab,
    keywordsPage,
    keywordSearch,
    keywordClusterFilter,
    keywordsSortBy,
    keywordsSortOrder,
  ]);

  // ─── API calls ────────────────────────────────────────────────────────────

  const authHeader = () => ({ Authorization: `Bearer mock-${userId}` });

  const fetchQuestions = async (
    projectId: string,
    page: number,
    search: string,
    typeFilter: string,
    sortBy: string,
    sortOrder: string
  ) => {
    setQuestionsLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: "10",
        search,
        question_type: typeFilter,
        sort_by: sortBy,
        sort_order: sortOrder,
      });
      const res = await fetch(
        `${API_BASE}/analysis/questions/${projectId}?${params}`,
        { headers: authHeader() }
      );
      const data = await res.json();
      if (res.ok) {
        setQuestionsData(data.questions || []);
        setQuestionsTotalCount(data.total_count || 0);
      }
    } catch (err) {
      console.error("Error fetching questions:", err);
    } finally {
      setQuestionsLoading(false);
    }
  };

  const fetchKeywords = async (
    projectId: string,
    page: number,
    search: string,
    typeFilter: string,
    sortBy: string,
    sortOrder: string
  ) => {
    setKeywordsLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: "10",
        search,
        keyword_type: typeFilter,
        sort_by: sortBy,
        sort_order: sortOrder,
      });
      const res = await fetch(
        `${API_BASE}/analysis/keywords/${projectId}?${params}`,
        { headers: authHeader() }
      );
      const data = await res.json();
      if (res.ok) {
        setKeywordsData(data.keywords || []);
        setKeywordsTotalCount(data.total_count || 0);
      }
    } catch (err) {
      console.error("Error fetching keywords:", err);
    } finally {
      setKeywordsLoading(false);
    }
  };

  const fetchProjects = async () => {
    try {
      setErrorMsg("");
      const res = await fetch(`${API_BASE}/projects`, {
        headers: authHeader(),
      });
      const data = await res.json();
      if (res.ok) {
        setProjects(data);
      } else {
        setErrorMsg(data.detail || "Failed to load projects.");
      }
    } catch {
      setErrorMsg(
        "Unable to connect to backend API server. Make sure the FastAPI backend is running."
      );
    }
  };

  const createProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projName || !projUrl) return;
    try {
      setErrorMsg("");
      const res = await fetch(`${API_BASE}/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader() },
        body: JSON.stringify({ name: projName, website_url: projUrl }),
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
    } catch {
      setErrorMsg("Error creating project.");
    }
  };

  const selectProject = (id: string) => {
    setSelectedProjectId(id);
    setActiveTab("overview");
    fetchProjectDetails(id);
  };

  const fetchBlogs = async (projectId: string) => {
    try {
      const res = await fetch(`${API_BASE}/blogs/${projectId}`, {
        headers: authHeader(),
      });
      const data = await res.json();
      if (res.ok) setBlogs(data);
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
        headers: { "Content-Type": "application/json", ...authHeader() },
        body: JSON.stringify({
          project_id: selectedProjectId,
          count: selectedBlogCount,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setBlogs(data);
      } else {
        setErrorMsg(data.detail || "Failed to generate blogs.");
      }
    } catch {
      setErrorMsg("Error generating blogs.");
    } finally {
      setGeneratingBlogs(false);
    }
  };

  const fetchProjectDetails = async (projectId: string) => {
    setLoading(true);
    setErrorMsg("");
    try {
      const [projRes, resRes, repRes] = await Promise.allSettled([
        fetch(`${API_BASE}/projects/${projectId}`, { headers: authHeader() }),
        fetch(`${API_BASE}/analysis/results/${projectId}`, {
          headers: authHeader(),
        }),
        fetch(`${API_BASE}/reports/${projectId}/latest`, {
          headers: authHeader(),
        }),
      ]);

      if (projRes.status === "fulfilled" && projRes.value.ok) {
        setProjectDetail(await projRes.value.json());
      }
      if (resRes.status === "fulfilled" && resRes.value.ok) {
        const resData = await resRes.value.json();
        setResults(resData);
        setQuestionsPage(1);
        setKeywordsPage(1);
      }
      if (repRes.status === "fulfilled" && repRes.value.ok) {
        setLatestReport(await repRes.value.json());
      } else {
        setLatestReport(null);
      }

      await fetchBlogs(projectId);
      setExpandedFactIds({});
    } catch {
      setErrorMsg("Error loading project details.");
    } finally {
      setLoading(false);
    }
  };

  const triggerAnalysisRun = async () => {
    if (!selectedProjectId) return;
    setErrorMsg("");
    try {
      const res = await fetch(
        `${API_BASE}/analysis/run/${selectedProjectId}`,
        { method: "POST", headers: authHeader() }
      );
      const data = await res.json();
      if (res.ok) {
        setActiveRun(data);
      } else {
        setErrorMsg(data.detail || "Failed to run analysis.");
      }
    } catch {
      setErrorMsg("Error starting analysis.");
    }
  };

  const deleteProject = async (id: string) => {
    if (!confirm("Are you sure you want to delete this project?")) return;
    try {
      const res = await fetch(`${API_BASE}/projects/${id}`, {
        method: "DELETE",
        headers: authHeader(),
      });
      if (res.ok) {
        setProjects((prev) => prev.filter((p) => p.id !== id));
        if (selectedProjectId === id) {
          setSelectedProjectId(null);
          setProjectDetail(null);
        }
      }
    } catch {
      setErrorMsg("Error deleting project.");
    }
  };

  const downloadReportRaw = async (format: string) => {
    if (!latestReport) return;
    try {
      const res = await fetch(
        `${API_BASE}/reports/download/${latestReport.id}/${format}`,
        { headers: authHeader() }
      );
      if (format === "json") {
        const data = await res.json();
        const dataStr =
          "data:text/json;charset=utf-8," +
          encodeURIComponent(JSON.stringify(data, null, 2));
        const a = document.createElement("a");
        a.setAttribute("href", dataStr);
        a.setAttribute(
          "download",
          `aivop_report_${selectedProjectId}.json`
        );
        document.body.appendChild(a);
        a.click();
        a.remove();
      } else {
        const data = await res.text();
        const dataStr =
          "data:text/markdown;charset=utf-8," + encodeURIComponent(data);
        const a = document.createElement("a");
        a.setAttribute("href", dataStr);
        a.setAttribute(
          "download",
          `aivop_report_${selectedProjectId}.md`
        );
        document.body.appendChild(a);
        a.click();
        a.remove();
      }
    } catch {
      setErrorMsg("Error downloading report.");
    }
  };

  // ─── Derived state ─────────────────────────────────────────────────────────

  const currentStatus =
    activeRun?.status || projectDetail?.status || "";
  const isRunning = RUNNING_STATUSES.includes(currentStatus);
  const progress = PROGRESS_MAP[currentStatus] ?? 0;
  const eta = ETA_MAP[currentStatus] ?? "0s";

  // ─── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="dashboard-layout">
      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
          >
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
          </svg>
          <span>AIVOP Dashboard</span>
        </div>

        {/* Multi-Tenancy Demo Switcher */}
        <div className="form-group" style={{ marginBottom: "2rem" }}>
          <label className="form-label">
            Active Workspace User (RLS Demo)
          </label>
          <select
            className="form-input"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            style={{
              padding: "0.5rem",
              borderRadius: "8px",
              background: "rgba(255,255,255,0.05)",
            }}
          >
            <option value="00000000-0000-4000-a000-000000000001">
              Preetham (User 1)
            </option>
            <option value="00000000-0000-4000-a000-000000000002">
              David Miller (User 2)
            </option>
            <option value="00000000-0000-4000-a000-000000000003">
              Sarah Connor (User 3)
            </option>
          </select>
        </div>

        <h3
          className="form-label"
          style={{ marginBottom: "0.5rem" }}
        >
          My Projects ({projects.length})
        </h3>
        <ul className="sidebar-menu">
          {projects.map((proj) => (
            <li
              key={proj.id}
              className={`sidebar-item ${
                selectedProjectId === proj.id ? "active" : ""
              }`}
            >
              <a
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  selectProject(proj.id);
                }}
                style={{ justifyContent: "space-between" }}
              >
                <span>{proj.project_name}</span>
                <span
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteProject(proj.id);
                  }}
                  style={{ opacity: 0.5, cursor: "pointer" }}
                >
                  ×
                </span>
              </a>
            </li>
          ))}
        </ul>
      </aside>

      {/* ── Main Panel ──────────────────────────────────────────────────── */}
      <main className="main-content">
        {/* Error banner */}
        {errorMsg && (
          <div
            className="card"
            style={{
              borderLeft: "4px solid var(--accent-red)",
              padding: "1rem",
              marginBottom: "2rem",
            }}
          >
            <p style={{ color: "HSL(0, 100%, 75%)", fontWeight: 600 }}>
              ⚠️ {errorMsg}
            </p>
          </div>
        )}

        {!selectedProjectId ? (
          /* ── Landing / Create Project ─────────────────────────────────── */
          <div>
            <h1
              className="text-gradient"
              style={{ fontSize: "2.8rem", marginBottom: "1rem" }}
            >
              AI Visibility Optimization Platform
            </h1>
            <p
              style={{
                color: "var(--text-muted)",
                fontSize: "1.1rem",
                marginBottom: "2.5rem",
                maxWidth: "800px",
              }}
            >
              Help your brand gain organic visibility inside AI Recommendation
              Systems like ChatGPT, Gemini, and Claude. Crawl website
              structures, extract verified facts, and generate optimization
              triggers.
            </p>

            <div className="card glow-border" style={{ maxWidth: "600px" }}>
              <h2 style={{ marginBottom: "1.5rem" }}>
                Create New Optimization Project
              </h2>
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
                <button
                  type="submit"
                  className="btn btn-primary"
                  style={{ width: "100%", marginTop: "1rem" }}
                >
                  Create Project &amp; Start
                </button>
              </form>
            </div>
          </div>
        ) : (
          /* ── Project Dashboard ──────────────────────────────────────────── */
          <div>
            {/* Project Header */}
            {projectDetail && (
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "2rem",
                }}
              >
                <div>
                  <h1
                    className="text-gradient"
                    style={{ fontSize: "2.4rem" }}
                  >
                    {projectDetail.project_name}
                  </h1>
                  <p style={{ color: "var(--text-muted)" }}>
                    🌐 Target Website:{" "}
                    <a
                      href={projectDetail.website_url}
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: "var(--secondary)" }}
                    >
                      {projectDetail.website_url}
                    </a>
                    {projectDetail.industry && (
                      <span
                        className="badge badge-info"
                        style={{ marginLeft: "1rem" }}
                      >
                        {projectDetail.industry}
                      </span>
                    )}
                  </p>
                </div>
                <div>
                  <button
                    className={`btn ${isRunning ? "btn-secondary" : "btn-primary"}`}
                    onClick={triggerAnalysisRun}
                    disabled={isRunning}
                  >
                    {isRunning ? (
                      <>
                        <div className="spinner"></div>
                        <span>
                          Processing ({currentStatus})...
                        </span>
                      </>
                    ) : (
                      <span>Run AI Crawler &amp; Agents</span>
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* ── Run Progress Banner ────────────────────────────────────── */}
            {isRunning && (
              <div
                className="card glow-border"
                style={{
                  marginBottom: "2rem",
                  background:
                    "linear-gradient(135deg, rgba(110, 0, 255, 0.08) 0%, rgba(0, 255, 136, 0.02) 100%)",
                  border: "1px solid var(--primary)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "1rem",
                  }}
                >
                  <div>
                    <h3
                      style={{
                        margin: 0,
                        fontSize: "1.25rem",
                        color: "var(--text-light)",
                      }}
                    >
                      Intelligence Pipeline Execution
                    </h3>
                    <p
                      style={{
                        color: "var(--text-muted)",
                        fontSize: "0.85rem",
                        margin: "0.25rem 0 0 0",
                      }}
                    >
                      Stage:{" "}
                      <span
                        style={{
                          textTransform: "capitalize",
                          fontWeight: "bold",
                          color: "var(--secondary)",
                        }}
                      >
                        {currentStatus}
                      </span>
                    </p>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <span
                      className="badge badge-warning"
                      style={{
                        textTransform: "capitalize",
                        fontSize: "0.85rem",
                        padding: "0.35rem 0.75rem",
                      }}
                    >
                      Active Agent:{" "}
                      {activeRun?.current_agent ||
                        projectDetail?.current_agent ||
                        "Scheduler"}
                    </span>
                  </div>
                </div>

                {/* Progress bar */}
                <div
                  style={{
                    width: "100%",
                    height: "8px",
                    background: "rgba(255, 255, 255, 0.05)",
                    borderRadius: "4px",
                    overflow: "hidden",
                    marginBottom: "1rem",
                  }}
                >
                  <div
                    style={{
                      width: `${progress}%`,
                      height: "100%",
                      background:
                        "linear-gradient(90deg, var(--primary) 0%, var(--secondary) 100%)",
                      transition: "width 0.5s ease-in-out",
                    }}
                  />
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(3, 1fr)",
                    gap: "1rem",
                    fontSize: "0.9rem",
                    color: "var(--text-muted)",
                  }}
                >
                  <div>
                    Progress:{" "}
                    <strong style={{ color: "var(--text-light)" }}>
                      {progress}%
                    </strong>
                  </div>
                  <div>
                    Elapsed Time:{" "}
                    <strong style={{ color: "var(--text-light)" }}>
                      {elapsedTime}s
                    </strong>
                  </div>
                  <div>
                    Est. Remaining:{" "}
                    <strong style={{ color: "var(--accent-amber)" }}>
                      {eta}
                    </strong>
                  </div>
                </div>
              </div>
            )}

            {/* ── Run Completed/Failed Banner ────────────────────────────── */}
            {activeRun &&
              ["completed", "failed"].includes(activeRun.status) && (
                <div
                  className="card"
                  style={{
                    marginBottom: "2rem",
                    borderLeft:
                      activeRun.status === "completed"
                        ? "4px solid var(--accent-green)"
                        : "4px solid var(--accent-red)",
                    background: "rgba(255, 255, 255, 0.02)",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div>
                      <h3
                        style={{
                          margin: 0,
                          color:
                            activeRun.status === "completed"
                              ? "var(--accent-green)"
                              : "var(--accent-red)",
                        }}
                      >
                        {activeRun.status === "completed"
                          ? "Pipeline Completed Successfully"
                          : "Pipeline Execution Failed"}
                      </h3>
                      <p
                        style={{
                          color: "var(--text-muted)",
                          fontSize: "0.85rem",
                          margin: "0.25rem 0 0 0",
                        }}
                      >
                        Run ID:{" "}
                        <span style={{ fontFamily: "monospace" }}>
                          {activeRun.id}
                        </span>
                      </p>
                    </div>
                    <button
                      className="btn btn-secondary"
                      style={{ padding: "0.25rem 0.5rem", fontSize: "0.8rem" }}
                      onClick={() => setActiveRun(null)}
                    >
                      Dismiss
                    </button>
                  </div>
                  {activeRun.error_message && (
                    <p
                      style={{
                        color: "var(--accent-red)",
                        marginTop: "0.5rem",
                        fontSize: "0.9rem",
                      }}
                    >
                      Reason: {activeRun.error_message}
                    </p>
                  )}
                </div>
              )}

            {/* ── Stats Overview ─────────────────────────────────────────── */}
            <div className="grid-3" style={{ marginBottom: "2.5rem" }}>
              <div className="metric-card">
                <div>
                  <div className="metric-title">Verified Facts Extracted</div>
                  <div className="metric-value">
                    {results.verified_facts.length}
                  </div>
                </div>
                <svg
                  width="32"
                  height="32"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="var(--accent-green)"
                  strokeWidth="2"
                >
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
              </div>
              <div className="metric-card">
                <div>
                  <div className="metric-title">LLM Queries Discovered</div>
                  <div className="metric-value">
                    {results.questions_count ?? 0}
                  </div>
                </div>
                <svg
                  width="32"
                  height="32"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="var(--secondary)"
                  strokeWidth="2"
                >
                  <circle cx="12" cy="12" r="10" />
                  <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
              </div>
              <div className="metric-card">
                <div>
                  <div className="metric-title">Semantic Keyword Clusters</div>
                  <div className="metric-value">
                    {results.keywords_count ?? 0}
                  </div>
                </div>
                <svg
                  width="32"
                  height="32"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="var(--primary)"
                  strokeWidth="2"
                >
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                  <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
                  <line x1="12" y1="22.08" x2="12" y2="12" />
                </svg>
              </div>
            </div>

            {/* ── Tab Navigation ─────────────────────────────────────────── */}
            <div
              className="tabs-bar"
              style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}
            >
              {[
                { key: "overview", label: "Overview" },
                { key: "bi", label: "Business Intelligence" },
                { key: "facts", label: "Verified Facts" },
                { key: "questions", label: "Question Discovery" },
                { key: "keywords", label: "Keyword Intelligence" },
                { key: "competitors", label: "Competitor Analysis" },
                { key: "content", label: "Content Opportunities" },
                { key: "blogs", label: "Generate Blogs" },
                { key: "reports", label: "Reports" },
                { key: "agent_monitor", label: "Agent Monitor" },
                { key: "rec_intel", label: "🧠 Recommendation Intelligence" },
                { key: "validation", label: "🔍 Validation" },
                { key: "reality_check", label: "🎯 Reality Checker" },
                { key: "benchmark", label: "📊 Competitor Benchmark" },
                { key: "tracker", label: "📈 Longitudinal Tracker" },
                { key: "analytics", label: "📊 Advanced Analytics" },
              ].map(({ key, label }) => (
                <button
                  key={key}
                  className={`tab-btn ${activeTab === key ? "active" : ""}`}
                  onClick={() => setActiveTab(key)}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* ── Tab Panels ─────────────────────────────────────────────── */}
            {loading ? (
              <div className="card flex-center" style={{ padding: "4rem" }}>
                <div className="spinner"></div>
                <p
                  style={{
                    color: "var(--text-muted)",
                    marginTop: "1rem",
                  }}
                >
                  Loading project data...
                </p>
              </div>
            ) : (
              <>
                {activeTab === "overview" && (
                  <OverviewTab
                    results={results}
                    latestReport={latestReport}
                    triggerAnalysisRun={triggerAnalysisRun}
                  />
                )}

                {activeTab === "bi" && (
                  <BusinessIntelligenceTab results={results} />
                )}

                {activeTab === "facts" && (
                  <VerifiedFactsTab
                    facts={results.verified_facts}
                    expandedFactIds={expandedFactIds}
                    onToggleExpand={(id) =>
                      setExpandedFactIds((prev) => ({
                        ...prev,
                        [id]: !prev[id],
                      }))
                    }
                  />
                )}

                {activeTab === "questions" && (
                  <QuestionDiscoveryTab
                    questionsData={questionsData}
                    questionsTotalCount={questionsTotalCount}
                    questionsPage={questionsPage}
                    questionsLoading={questionsLoading}
                    questionSearch={questionSearch}
                    questionTypeFilter={questionTypeFilter}
                    questionsSortBy={questionsSortBy}
                    questionsSortOrder={questionsSortOrder}
                    questionsCategories={results.questions_categories || []}
                    onSearchChange={(v) => {
                      setQuestionSearch(v);
                      setQuestionsPage(1);
                    }}
                    onTypeFilterChange={(v) => {
                      setQuestionTypeFilter(v);
                      setQuestionsPage(1);
                    }}
                    onSortChange={(by, order) => {
                      setQuestionsSortBy(by);
                      setQuestionsSortOrder(order);
                      setQuestionsPage(1);
                    }}
                    onPrevPage={() =>
                      setQuestionsPage((p) => Math.max(1, p - 1))
                    }
                    onNextPage={() => setQuestionsPage((p) => p + 1)}
                  />
                )}

                {activeTab === "keywords" && (
                  <KeywordIntelligenceTab
                    keywordsData={keywordsData}
                    keywordsTotalCount={keywordsTotalCount}
                    keywordsPage={keywordsPage}
                    keywordsLoading={keywordsLoading}
                    keywordSearch={keywordSearch}
                    keywordClusterFilter={keywordClusterFilter}
                    keywordsSortBy={keywordsSortBy}
                    keywordsSortOrder={keywordsSortOrder}
                    keywordsCategories={results.keywords_categories || []}
                    onSearchChange={(v) => {
                      setKeywordSearch(v);
                      setKeywordsPage(1);
                    }}
                    onClusterFilterChange={(v) => {
                      setKeywordClusterFilter(v);
                      setKeywordsPage(1);
                    }}
                    onSortChange={(by, order) => {
                      setKeywordsSortBy(by);
                      setKeywordsSortOrder(order);
                      setKeywordsPage(1);
                    }}
                    onPrevPage={() =>
                      setKeywordsPage((p) => Math.max(1, p - 1))
                    }
                    onNextPage={() => setKeywordsPage((p) => p + 1)}
                  />
                )}

                {activeTab === "competitors" && (
                  <CompetitorAnalysisTab
                    competitors={results.competitors}
                    competitorFeatureMatrix={results.competitor_feature_matrix}
                  />
                )}

                {activeTab === "content" && (
                  <ContentOpportunitiesTab
                    contentOpportunities={results.content_opportunities}
                    contentCoverage={results.content_coverage}
                    gapAnalysis={results.gap_analysis}
                  />
                )}

                {activeTab === "blogs" && (
                  <GenerateBlogsTab
                    blogs={blogs}
                    selectedBlogCount={selectedBlogCount}
                    generatingBlogs={generatingBlogs}
                    onSelectCount={setSelectedBlogCount}
                    onGenerate={triggerBlogGeneration}
                  />
                )}

                {activeTab === "reports" && (
                  <ReportsTab
                    latestReport={latestReport}
                    selectedProjectId={selectedProjectId}
                    onDownload={downloadReportRaw}
                  />
                )}

                {activeTab === "agent_monitor" && (
                  <AgentMonitorTab
                    agentRuns={results.agent_runs}
                    extractionFailures={results.extraction_failures}
                  />
                )}

                {activeTab === "rec_intel" && selectedProjectId && (
                  <RecommendationIntelligenceTab
                    projectId={selectedProjectId}
                    userId={userId}
                  />
                )}

                {activeTab === "validation" && selectedProjectId && (
                  <ValidationTab
                    projectId={selectedProjectId}
                    userId={userId}
                  />
                )}

                {activeTab === "reality_check" && selectedProjectId && (
                  <RealityCheckerTab
                    projectId={selectedProjectId}
                  />
                )}

                {activeTab === "benchmark" && selectedProjectId && (
                  <CompetitorBenchmarkTab
                    projectId={selectedProjectId}
                  />
                )}

                {activeTab === "tracker" && selectedProjectId && (
                  <LongitudinalTrackerTab
                    projectId={selectedProjectId}
                  />
                )}

                {activeTab === "analytics" && selectedProjectId && (
                  <AdvancedAnalyticsTab
                    projectId={selectedProjectId}
                  />
                )}
              </>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
