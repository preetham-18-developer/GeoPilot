"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { WorkspaceProvider, useWorkspace } from "./contexts/WorkspaceContext";
import { useProjectDetails } from "./hooks/useProjectDetails";
import { useRunPolling } from "./hooks/useRunPolling";
import { useQuestions, useKeywords } from "./hooks/usePaginatedData";
import { Sidebar, SECTION_SUBTABS, type MainSection } from "./components/ui/Sidebar";
import { CommandPalette, useCommandPalette } from "./components/ui/CommandPalette";
import { ErrorState, LoadingPage } from "./components/ui/SkeletonLoader";
import { PROGRESS_MAP, ETA_MAP } from "./lib/config";
import { ErrorBoundary } from "./components/ui/ErrorBoundary";
import { ToastProvider, useToast } from "./components/ui/Toast";

// ── Tab Components ────────────────────────────────────────────
import OverviewTab from "./components/OverviewTab";
import VerifiedFactsTab from "./components/VerifiedFactsTab";
import QuestionDiscoveryTab from "./components/QuestionDiscoveryTab";
import KeywordIntelligenceTab from "./components/KeywordIntelligenceTab";
import CompetitorAnalysisTab from "./components/CompetitorAnalysisTab";
import ContentOpportunitiesTab from "./components/ContentOpportunitiesTab";
import GenerateBlogsTab from "./components/GenerateBlogsTab";
import AgentMonitorTab from "./components/AgentMonitorTab";
import ValidationTab from "./components/ValidationTab";
import RecommendationIntelligenceTab from "./components/RecommendationIntelligenceTab";
import RealityCheckerTab from "./components/RealityCheckerTab";
import CompetitorBenchmarkTab from "./components/CompetitorBenchmarkTab";
import LongitudinalTrackerTab from "./components/LongitudinalTrackerTab";
import AdvancedAnalyticsTab from "./components/AdvancedAnalyticsTab";
import ContentIntelligenceTab from "./components/ContentIntelligenceTab";
import ReliabilityDashboard from "./components/ReliabilityDashboard";
import GEOIntelligenceTab from "./components/GEOIntelligenceTab";
import OptimizationIntelligenceTab from "./components/OptimizationIntelligenceTab";
import AutonomousExecutionTab from "./components/AutonomousExecutionTab";

// Workspace Components
import SearchKeywordsWorkspace from "./components/workspaces/SearchKeywordsWorkspace";
import CompetitorWorkspace from "./components/workspaces/CompetitorWorkspace";
import SimulationWorkspace from "./components/workspaces/SimulationWorkspace";
import ContentStudioWorkspace from "./components/workspaces/ContentStudioWorkspace";
import SystemHealthWorkspace from "./components/workspaces/SystemHealthWorkspace";

// ─────────────────────────────────────────────────────────────
// Inner dashboard — consumes workspace context
// ─────────────────────────────────────────────────────────────
function AivopDashboardInner() {
  const { userId, setUserId, projects, createProject, deleteProject, errorMsg: wsError, clearError } = useWorkspace();

  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<MainSection>("overview");
  const [activeSubTab, setActiveSubTab] = useState("overview");
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [generatingBlogs, setGeneratingBlogs] = useState(false);
  const [selectedBlogCount, setSelectedBlogCount] = useState(10);

  const cmdPalette = useCommandPalette();
  const toast = useToast();

  // ── Project data hook ──────────────────────────────────────
  const proj = useProjectDetails(userId);

  // ── Question & keyword hooks ───────────────────────────────
  const qHook = useQuestions(userId);
  const kHook = useKeywords(userId);

  // ── Run polling ────────────────────────────────────────────
  useRunPolling({
    activeRun: proj.activeRun,
    projectDetail: proj.projectDetail,
    userId,
    selectedProjectId,
    setActiveRun: proj.setActiveRun,
    setProjectDetail: proj.setProjectDetail,
    setElapsedTime: proj.setElapsedTime,
    onRunComplete: (id) => {
      proj.fetchProjectDetails(id);
    },
  });

  // ── Fetch questions when tab changes ───────────────────────
  useEffect(() => {
    if (selectedProjectId && activeSubTab === "questions") {
      qHook.fetchQuestions(
        selectedProjectId,
        qHook.questionsPage,
        qHook.questionSearch,
        qHook.questionTypeFilter,
        qHook.questionsSortBy,
        qHook.questionsSortOrder
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProjectId, activeSubTab, qHook.questionsPage, qHook.questionSearch, qHook.questionTypeFilter, qHook.questionsSortBy, qHook.questionsSortOrder]);

  // ── Fetch keywords when tab changes ────────────────────────
  useEffect(() => {
    if (selectedProjectId && activeSubTab === "keywords") {
      kHook.fetchKeywords(
        selectedProjectId,
        kHook.keywordsPage,
        kHook.keywordSearch,
        kHook.keywordClusterFilter,
        kHook.keywordsSortBy,
        kHook.keywordsSortOrder
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProjectId, activeSubTab, kHook.keywordsPage, kHook.keywordSearch, kHook.keywordClusterFilter, kHook.keywordsSortBy, kHook.keywordsSortOrder]);

  // ── Project selection ──────────────────────────────────────
  const handleSelectProject = useCallback((id: string) => {
    setSelectedProjectId(id);
    setActiveSection("overview");
    setActiveSubTab("overview");
    proj.resetProjectState();
    proj.fetchProjectDetails(id);
    qHook.resetQuestions();
    kHook.resetKeywords();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── User switch: reset everything ─────────────────────────
  useEffect(() => {
    setSelectedProjectId(null);
    proj.resetProjectState();
    qHook.resetQuestions();
    kHook.resetKeywords();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const handleSectionChange = useCallback((section: MainSection, subTab: string) => {
    setActiveSection(section);
    setActiveSubTab(subTab);
  }, []);

  const handleCreateProject = useCallback(async (name: string, url: string) => {
    try {
      const p = await createProject(name, url);
      if (p) {
        handleSelectProject(p.id);
        toast.success("Project Created", `Created project "${name}" successfully.`);
      } else {
        toast.error("Creation Failed", "Failed to create project.");
      }
    } catch {
      toast.error("Creation Failed", "An error occurred while creating project.");
    }
  }, [createProject, handleSelectProject, toast]);

  const handleDeleteProject = useCallback(async (id: string) => {
    const projName = projects.find(p => p.id === id)?.project_name || "Project";
    try {
      await deleteProject(id);
      toast.success("Project Deleted", `"${projName}" has been successfully deleted.`);
    } catch {
      toast.error("Deletion Failed", `Could not delete project "${projName}".`);
    }
  }, [deleteProject, projects, toast]);

  const handleTriggerAnalysisRun = useCallback(async (pid: string) => {
    toast.info("Pipeline Initiated", "Starting multi-agent GEO analysis...");
    await proj.triggerAnalysisRun(pid);
  }, [proj, toast]);

  // Toast on run status changes
  const lastToastedRunRef = useRef<{ id: string; status: string } | null>(null);
  useEffect(() => {
    if (!proj.activeRun) return;
    const runId = proj.activeRun.id;
    const runStatus = proj.activeRun.status;
    if (lastToastedRunRef.current?.id === runId && lastToastedRunRef.current?.status === runStatus) {
      return;
    }
    if (runStatus === "completed") {
      lastToastedRunRef.current = { id: runId, status: runStatus };
      toast.success("Analysis Complete", "All GEO agents finished processing successfully.");
    } else if (["failed", "FAILED_VALIDATION", "FAILED_GROUNDING"].includes(runStatus)) {
      lastToastedRunRef.current = { id: runId, status: runStatus };
      toast.error("Analysis Failed", proj.activeRun.error_message || "An error occurred during execution.");
    }
  }, [proj.activeRun, toast]);

  const handleBlogGenerate = useCallback(async () => {
    if (!selectedProjectId) return;
    setGeneratingBlogs(true);
    toast.info("Content Studio", `Generating ${selectedBlogCount} optimized blog posts...`);
    const success = await proj.triggerBlogGeneration(selectedProjectId, selectedBlogCount);
    setGeneratingBlogs(false);
    if (success) {
      toast.success("Blogs Generated", `Successfully generated ${selectedBlogCount} blog posts.`);
    } else {
      toast.error("Generation Failed", "Failed to generate blog posts based on verified facts.");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProjectId, selectedBlogCount, toast]);

  // ── Command Palette items ──────────────────────────────────
  const commandItems = useMemo(() => {
    const items: any[] = [];
    // Sections
    Object.entries(SECTION_SUBTABS).forEach(([section, subtabs]) => {
      subtabs.forEach((sub) => {
        items.push({
          id: `nav-${section}-${sub.key}`,
          type: "section",
          label: sub.label,
          description: section,
          onSelect: () => handleSectionChange(section as MainSection, sub.key),
        });
      });
    });
    // Projects
    projects.forEach((p) => {
      items.push({
        id: `proj-${p.id}`,
        type: "project",
        label: p.project_name,
        description: p.website_url,
        onSelect: () => handleSelectProject(p.id),
      });
    });
    return items;
  }, [projects, handleSectionChange, handleSelectProject]);

  // ── Render tab panel ───────────────────────────────────────
  const renderTabPanel = () => {
    if (!selectedProjectId) return null;
    if (proj.loading) return <LoadingPage label="Loading project data..." />;

    const pid = selectedProjectId;
    const r = proj.results;

    switch (activeSection) {
      case "overview":
        return (
          <OverviewTab
            projectId={pid}
            userId={userId}
            results={r}
            latestReport={proj.latestReport}
            triggerAnalysisRun={() => handleTriggerAnalysisRun(pid)}
            projectDetail={proj.projectDetail}
            onDownloadReport={(fmt) => proj.latestReport && proj.downloadReport(proj.latestReport.id, pid, fmt)}
          />
        );
      case "search_intel":
        return <SearchKeywordsWorkspace projectId={pid} userId={userId} results={r} qHook={qHook} kHook={kHook} />;
      case "competitor_intel":
        return <CompetitorWorkspace projectId={pid} userId={userId} results={r} />;
      case "simulation":
        return <SimulationWorkspace projectId={pid} userId={userId} />;
      case "content_studio":
        return (
          <ContentStudioWorkspace
            projectId={pid}
            userId={userId}
            results={r}
            blogs={proj.blogs}
            selectedBlogCount={selectedBlogCount}
            generatingBlogs={generatingBlogs}
            onSelectCount={setSelectedBlogCount}
            onGenerate={handleBlogGenerate}
          />
        );
      case "system_health":
        return <SystemHealthWorkspace projectId={pid} userId={userId} results={r} />;
      default:
        return null;
    }
  };

  const renderTabPanelWithBoundary = () => {
    const panel = renderTabPanel();
    if (!panel) return null;
    return (
      <ErrorBoundary componentName={`${activeSubTab.charAt(0).toUpperCase() + activeSubTab.slice(1)}Tab`}>
        {panel}
      </ErrorBoundary>
    );
  };

  // ── Run progress banner ────────────────────────────────────
  const progress = PROGRESS_MAP[proj.currentStatus] ?? 0;
  const eta = ETA_MAP[proj.currentStatus] ?? "0s";

  return (
    <div className="dashboard-layout">
      {/* Mobile hamburger */}
      <button
        className="mobile-hamburger btn btn-ghost btn-icon"
        style={{ position: "fixed", top: "1rem", left: "1rem", zIndex: 150 }}
        onClick={() => setIsMobileSidebarOpen(true)}
        aria-label="Open navigation"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>

      {/* Sidebar */}
      <Sidebar
        userId={userId}
        setUserId={setUserId}
        projects={projects}
        selectedProjectId={selectedProjectId}
        onSelectProject={handleSelectProject}
        onDeleteProject={handleDeleteProject}
        onCreateProject={handleCreateProject}
        activeSection={activeSection}
        activeSubTab={activeSubTab}
        onSectionChange={handleSectionChange}
        onCommandPaletteOpen={cmdPalette.open}
        isMobileOpen={isMobileSidebarOpen}
        onMobileClose={() => setIsMobileSidebarOpen(false)}
      />

      {/* Main Content */}
      <main className="main-content">
        {/* Global error */}
        {(wsError || proj.errorMsg) && (
          <ErrorState
            message={wsError || proj.errorMsg}
            onRetry={() => { clearError(); proj.setErrorMsg(""); }}
          />
        )}

        {!selectedProjectId ? (
          /* ── Landing ──────────────────────────────────────────── */
          <div className="animate-fade-in" style={{ maxWidth: 640, margin: "4rem auto" }}>
            <div style={{ marginBottom: "2.5rem" }}>
              <h1 className="text-gradient" style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>
                AI Visibility Optimization
              </h1>
              <p style={{ fontSize: "1.0625rem", color: "var(--text-muted)", lineHeight: 1.7 }}>
                Help your brand gain organic visibility inside AI systems like ChatGPT, Gemini, and Claude.
                Select a project from the sidebar, or create a new one below.
              </p>
            </div>
            <div className="card glow-border">
              <h2 style={{ marginBottom: "1.5rem", fontSize: "1.125rem" }}>Create New Project</h2>
              <form onSubmit={(e) => {
                e.preventDefault();
                const fd = new FormData(e.currentTarget);
                handleCreateProject(fd.get("name") as string, fd.get("url") as string);
                (e.target as HTMLFormElement).reset();
              }}>
                <div className="form-group mb-4">
                  <label className="form-label">Project Name</label>
                  <input name="name" type="text" className="form-input" placeholder="e.g. Acme SaaS CRM" required />
                </div>
                <div className="form-group mb-4">
                  <label className="form-label">Company Website URL</label>
                  <input name="url" type="url" className="form-input" placeholder="https://acme-crm.com" required />
                </div>
                <button type="submit" className="btn btn-primary" style={{ width: "100%" }}>
                  Create Project &amp; Start
                </button>
              </form>
            </div>
          </div>
        ) : (
          /* ── Project Dashboard ─────────────────────────────────── */
          <div>
            {/* Project header */}
            {proj.projectDetail && (
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h1 className="text-gradient" style={{ fontSize: "1.75rem" }}>
                    {proj.projectDetail.project_name}
                  </h1>
                  <div className="flex items-center gap-3 mt-1">
                    <a
                      href={proj.projectDetail.website_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: "var(--secondary)", fontSize: "0.875rem" }}
                    >
                      {proj.projectDetail.website_url}
                    </a>
                    {proj.projectDetail.industry && (
                      <span className="badge badge-info">{proj.projectDetail.industry}</span>
                    )}
                  </div>
                </div>
                <button
                  className={`btn ${proj.isRunning ? "btn-secondary" : "btn-primary"}`}
                  onClick={() => handleTriggerAnalysisRun(selectedProjectId)}
                  disabled={proj.isRunning}
                >
                  {proj.isRunning ? (
                    <>
                      <div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                      {proj.currentStatus}...
                    </>
                  ) : (
                    <>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <polygon points="5 3 19 12 5 21 5 3" />
                      </svg>
                      Run Analysis
                    </>
                  )}
                </button>
              </div>
            )}

            {/* Run Progress Banner */}
            {proj.isRunning && (
              <div className="run-banner mb-6 animate-fade-in">
                <div className="run-banner-header">
                  <div>
                    <div style={{ fontWeight: 600, fontSize: "0.9375rem" }}>Pipeline Executing</div>
                    <div style={{ fontSize: "0.8125rem", color: "var(--text-dark)", marginTop: 2 }}>
                      Stage: <span style={{ color: "var(--secondary)", fontWeight: 600, textTransform: "capitalize" }}>{proj.currentStatus}</span>
                      {" · "}
                      Agent: <span style={{ color: "var(--text-muted)" }}>{proj.activeRun?.current_agent ?? proj.projectDetail?.current_agent ?? "Scheduler"}</span>
                    </div>
                  </div>
                  <div style={{ fontSize: "0.8125rem", color: "var(--text-dark)", textAlign: "right" }}>
                    <div><span style={{ color: "var(--text-muted)" }}>{proj.elapsedTime}s</span> elapsed</div>
                    <div>ETA: <span style={{ color: "var(--accent-amber)" }}>{eta}</span></div>
                  </div>
                </div>
                <div className="progress-bar-track">
                  <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
                </div>
              </div>
            )}

            {/* Completed/Failed Banner */}
            {proj.activeRun && ["completed", "failed", "FAILED_VALIDATION", "FAILED_GROUNDING"].includes(proj.activeRun.status) && (
              <div
                className="card mb-6 animate-fade-in"
                style={{ borderLeft: `3px solid ${proj.activeRun.status === "completed" ? "var(--accent-green)" : "var(--accent-red)"}` }}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div style={{ fontWeight: 600, color: proj.activeRun.status === "completed" ? "var(--accent-green)" : "var(--accent-red)" }}>
                      {proj.activeRun.status === "completed" ? "✓ Pipeline Completed" : "✗ Pipeline Failed"}
                    </div>
                    {proj.activeRun.error_message && (
                      <p style={{ color: "var(--accent-red)", fontSize: "0.8125rem", marginTop: 4 }}>
                        {proj.activeRun.error_message}
                      </p>
                    )}
                  </div>
                  <button className="btn btn-ghost btn-sm" onClick={() => proj.setActiveRun(null)}>
                    Dismiss
                  </button>
                </div>
              </div>
            )}

            {/* Active section sub-tabs */}
            {SECTION_SUBTABS[activeSection].length > 1 && (
              <div className="tabs-bar mb-6">
                {SECTION_SUBTABS[activeSection].map(({ key, label }) => (
                  <button
                    key={key}
                    className={`tab-btn ${activeSubTab === key ? "active" : ""}`}
                    onClick={() => setActiveSubTab(key)}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}

            {/* Tab Panel */}
            {renderTabPanelWithBoundary()}
          </div>
        )}
      </main>

      {/* Command Palette */}
      <CommandPalette
        isOpen={cmdPalette.isOpen}
        onClose={cmdPalette.close}
        items={commandItems}
      />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Root export — wraps with ErrorBoundary, ToastProvider, and WorkspaceProvider
// ─────────────────────────────────────────────────────────────
export default function AivopDashboard() {
  return (
    <ErrorBoundary componentName="AivopDashboard">
      <ToastProvider>
        <WorkspaceProvider>
          <AivopDashboardInner />
        </WorkspaceProvider>
      </ToastProvider>
    </ErrorBoundary>
  );
}
