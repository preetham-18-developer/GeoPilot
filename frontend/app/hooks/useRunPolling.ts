"use client";

import { useEffect, useRef } from "react";
import { API_BASE, authHeader, RUNNING_STATUSES, PROGRESS_MAP } from "../lib/config";

interface UseRunPollingOptions {
  activeRun: any;
  projectDetail: any;
  userId: string;
  selectedProjectId: string | null;
  setActiveRun: (run: any) => void;
  setProjectDetail: (detail: any) => void;
  setElapsedTime: (time: number) => void;
  onRunComplete: (projectId: string) => void;
}

/**
 * Manages the 3 polling loops previously inline in page.tsx:
 * 1. Active run status polling (every 3s)
 * 2. Project status polling for page-refresh recovery (every 3s)
 * 3. Elapsed time counter (every 1s)
 */
export function useRunPolling({
  activeRun,
  projectDetail,
  userId,
  selectedProjectId,
  setActiveRun,
  setProjectDetail,
  setElapsedTime,
  onRunComplete,
}: UseRunPollingOptions) {
  const onRunCompleteRef = useRef(onRunComplete);
  onRunCompleteRef.current = onRunComplete;

  // ── Poll active run status ──────────────────────────────────────
  useEffect(() => {
    if (!activeRun || !RUNNING_STATUSES.includes(activeRun.status)) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/analysis/status/${activeRun.id}`, {
          headers: authHeader(userId),
        });
        if (!res.ok) return;
        const data = await res.json();
        setActiveRun(data);
        if (["completed", "failed", "FAILED_VALIDATION", "FAILED_GROUNDING"].includes(data.status)) {
          clearInterval(interval);
          if (selectedProjectId) onRunCompleteRef.current(selectedProjectId);
        }
      } catch (err) {
        console.error("Run polling error:", err);
      }
    }, 3000);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeRun?.id, activeRun?.status, userId, selectedProjectId, setActiveRun]);

  // ── Poll project status (handles page-refresh recovery) ─────────
  useEffect(() => {
    if (!selectedProjectId || !projectDetail) return;
    const isPollingStatus = RUNNING_STATUSES.filter((s) => s !== "pending").includes(
      projectDetail.status
    );
    if (!isPollingStatus) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/projects/${selectedProjectId}`, {
          headers: authHeader(userId),
        });
        if (!res.ok) return;
        const data = await res.json();
        setProjectDetail(data);
        if (["completed", "failed", "FAILED_VALIDATION", "FAILED_GROUNDING"].includes(data.status)) {
          clearInterval(interval);
          onRunCompleteRef.current(selectedProjectId);
        }
      } catch (err) {
        console.error("Project status polling error:", err);
      }
    }, 3000);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectDetail?.status, selectedProjectId, userId, setProjectDetail]);

  // ── Elapsed time counter ────────────────────────────────────────
  useEffect(() => {
    const activeStatus = activeRun?.status ?? projectDetail?.status ?? "";
    const isRunning = RUNNING_STATUSES.filter((s) => s !== "pending").includes(activeStatus);
    const startTimestamp = activeRun?.started_at ?? projectDetail?.created_at;

    if (!isRunning || !startTimestamp) {
      setElapsedTime(0);
      return;
    }

    const calcElapsed = () =>
      Math.max(0, Math.floor((Date.now() - new Date(startTimestamp).getTime()) / 1000));

    setElapsedTime(calcElapsed());
    const timer = setInterval(() => setElapsedTime(calcElapsed()), 1000);
    return () => clearInterval(timer);
  }, [
    activeRun?.status,
    projectDetail?.status,
    activeRun?.started_at,
    projectDetail?.created_at,
    setElapsedTime,
  ]);
}
