"use client";

import { useState, useCallback, useEffect } from "react";
import { API_BASE, authHeader, RUNNING_STATUSES, PROGRESS_MAP, ETA_MAP } from "../lib/config";

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

export interface ProjectDetail {
  id: string;
  project_name: string;
  website_url: string;
  status: string;
  industry?: string;
  current_agent?: string;
  created_at?: string;
  started_at?: string;
}

export interface RunInfo {
  id: string;
  status: string;
  error_message?: string;
  current_agent?: string;
  started_at?: string;
}

export function useProjectDetails(userId: string) {
  const [projectDetail, setProjectDetail] = useState<ProjectDetail | null>(null);
  const [results, setResults] = useState<any>(EMPTY_RESULTS);
  const [latestReport, setLatestReport] = useState<any>(null);
  const [blogs, setBlogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  // Active run tracking
  const [activeRun, setActiveRun] = useState<RunInfo | null>(null);
  const [elapsedTime, setElapsedTime] = useState(0);

  // Expanded fact IDs
  const [expandedFactIds, setExpandedFactIds] = useState<Record<string, boolean>>({});

  const resetProjectState = useCallback(() => {
    setProjectDetail(null);
    setResults(EMPTY_RESULTS);
    setLatestReport(null);
    setBlogs([]);
    setActiveRun(null);
    setElapsedTime(0);
    setExpandedFactIds({});
    setErrorMsg("");
  }, []);

  const fetchBlogs = useCallback(
    async (projectId: string) => {
      try {
        const res = await fetch(`${API_BASE}/blogs/${projectId}`, { headers: authHeader(userId) });
        if (res.ok) setBlogs(await res.json());
      } catch (err) {
        console.error("Error fetching blogs:", err);
      }
    },
    [userId]
  );

  const fetchProjectDetails = useCallback(
    async (projectId: string) => {
      setLoading(true);
      setErrorMsg("");
      try {
        const [projRes, resRes, repRes] = await Promise.allSettled([
          fetch(`${API_BASE}/projects/${projectId}`, { headers: authHeader(userId) }),
          fetch(`${API_BASE}/analysis/results/${projectId}`, { headers: authHeader(userId) }),
          fetch(`${API_BASE}/reports/${projectId}/latest`, { headers: authHeader(userId) }),
        ]);

        if (projRes.status === "fulfilled" && projRes.value.ok) {
          setProjectDetail(await projRes.value.json());
        }
        if (resRes.status === "fulfilled" && resRes.value.ok) {
          setResults(await resRes.value.json());
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
    },
    [userId, fetchBlogs]
  );

  const triggerAnalysisRun = useCallback(
    async (projectId: string) => {
      setErrorMsg("");
      try {
        const res = await fetch(`${API_BASE}/analysis/run/${projectId}`, {
          method: "POST",
          headers: authHeader(userId),
        });
        const data = await res.json();
        if (res.ok) {
          setActiveRun(data);
        } else {
          setErrorMsg(data.detail ?? "Failed to run analysis.");
        }
      } catch {
        setErrorMsg("Error starting analysis.");
      }
    },
    [userId]
  );

  const triggerBlogGeneration = useCallback(
    async (projectId: string, count: number) => {
      try {
        const res = await fetch(`${API_BASE}/blogs/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...authHeader(userId) },
          body: JSON.stringify({ project_id: projectId, count }),
        });
        const data = await res.json();
        if (res.ok) {
          setBlogs(data);
          return true;
        } else {
          setErrorMsg(data.detail ?? "Failed to generate blogs.");
          return false;
        }
      } catch {
        setErrorMsg("Error generating blogs.");
        return false;
      }
    },
    [userId]
  );

  const downloadReport = useCallback(
    async (reportId: string, projectId: string, format: "json" | "md") => {
      try {
        const res = await fetch(`${API_BASE}/reports/download/${reportId}/${format}`, {
          headers: authHeader(userId),
        });
        const ext = format === "json" ? "json" : "md";
        const mimeType = format === "json" ? "application/json" : "text/markdown";
        const content = format === "json"
          ? JSON.stringify(await res.json(), null, 2)
          : await res.text();
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `aivop_report_${projectId}.${ext}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      } catch {
        setErrorMsg("Error downloading report.");
      }
    },
    [userId]
  );

  const toggleFactExpand = useCallback((id: string) => {
    setExpandedFactIds((prev) => ({ ...prev, [id]: !prev[id] }));
  }, []);

  // Derived: run status info
  const currentStatus = activeRun?.status ?? projectDetail?.status ?? "";
  const isRunning = activeRun
    ? RUNNING_STATUSES.includes(activeRun.status as any)
    : !!(projectDetail?.status && projectDetail.status !== "pending" && RUNNING_STATUSES.includes(projectDetail.status as any));
  const progress = PROGRESS_MAP[currentStatus] ?? 0;
  const eta = ETA_MAP[currentStatus] ?? "0s";

  return {
    projectDetail,
    setProjectDetail,
    results,
    latestReport,
    blogs,
    loading,
    errorMsg,
    setErrorMsg,
    activeRun,
    setActiveRun,
    elapsedTime,
    setElapsedTime,
    expandedFactIds,
    toggleFactExpand,
    isRunning,
    currentStatus,
    progress,
    eta,
    fetchProjectDetails,
    fetchBlogs,
    triggerAnalysisRun,
    triggerBlogGeneration,
    downloadReport,
    resetProjectState,
  };
}
