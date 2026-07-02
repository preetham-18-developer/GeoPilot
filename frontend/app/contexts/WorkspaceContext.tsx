"use client";

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { API_BASE, authHeader, DEMO_USERS, DEFAULT_USER_ID } from "../lib/config";

interface Project {
  id: string;
  project_name: string;
  website_url: string;
  status: string;
  industry?: string;
  created_at?: string;
}

interface WorkspaceContextValue {
  userId: string;
  setUserId: (id: string) => void;
  projects: Project[];
  fetchProjects: () => Promise<void>;
  projectsLoading: boolean;
  createProject: (name: string, url: string) => Promise<Project | null>;
  deleteProject: (id: string) => Promise<void>;
  errorMsg: string;
  clearError: () => void;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [userId, setUserIdState] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('userId');
      // Migrate away from old fake/demo UUIDs that don't exist in auth.users.
      // Any stored ID that isn't a real Supabase UID must be discarded.
      const LEGACY_FAKE_IDS = [
        '00000000-0000-4000-a000-000000000001',
        '00000000-0000-4000-a000-000000000002',
        '00000000-0000-4000-a000-000000000003',
      ];
      if (stored && LEGACY_FAKE_IDS.includes(stored)) {
        // Replace stale fake ID with the real Supabase auth UID
        localStorage.setItem('userId', DEFAULT_USER_ID);
        return DEFAULT_USER_ID;
      }
      return stored || DEFAULT_USER_ID;
    }
    return DEFAULT_USER_ID;
  });
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const clearError = useCallback(() => setErrorMsg(""), []);

  const fetchProjects = useCallback(async () => {
    setProjectsLoading(true);
    setErrorMsg("");
    try {
      const res = await fetch(`${API_BASE}/projects`, { headers: authHeader(userId) });
      const data = await res.json();
      if (res.ok) {
        setProjects(data);
      } else {
        setErrorMsg(data.detail ?? "Failed to load projects.");
      }
    } catch {
      setErrorMsg("Unable to connect to backend. Ensure FastAPI is running on port 8000.");
    } finally {
      setProjectsLoading(false);
    }
  }, [userId]);

  const setUserId = useCallback((id: string) => {
    setUserIdState(id);
    setProjects([]);
  }, []);

  // Re-fetch projects whenever userId changes
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("userId", userId);
    }
    fetchProjects();
  }, [fetchProjects, userId]);

  const createProject = useCallback(
    async (name: string, url: string): Promise<Project | null> => {
      setErrorMsg("");
      try {
        const res = await fetch(`${API_BASE}/projects`, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...authHeader(userId) },
          body: JSON.stringify({ name, website_url: url }),
        });
        const data = await res.json();
        if (res.ok) {
          await fetchProjects();
          return data as Project;
        } else {
          setErrorMsg(data.detail ?? "Failed to create project.");
          return null;
        }
      } catch {
        setErrorMsg("Error creating project.");
        return null;
      }
    },
    [userId, fetchProjects]
  );

  const deleteProject = useCallback(
    async (id: string) => {
      // Optimistic update: remove project from state immediately
      setProjects((prev) => prev.filter((p) => p.id !== id));

      try {
        const res = await fetch(`${API_BASE}/projects/${id}`, {
          method: "DELETE",
          headers: authHeader(userId),
        });
        if (!res.ok) {
          // Revert optimistic update on backend failure
          await fetchProjects();
          const data = await res.json();
          setErrorMsg(data.detail ?? "Failed to delete project.");
        }
      } catch {
        // Revert optimistic update on network/unhandled exception
        await fetchProjects();
        setErrorMsg("Error deleting project.");
      }
    },
    [userId, fetchProjects]
  );

  return (
    <WorkspaceContext.Provider
      value={{
        userId,
        setUserId,
        projects,
        fetchProjects,
        projectsLoading,
        createProject,
        deleteProject,
        errorMsg,
        clearError,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace(): WorkspaceContextValue {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace must be used inside <WorkspaceProvider>");
  return ctx;
}

export { DEMO_USERS };
