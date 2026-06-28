"use client";

import React, { useState } from "react";
import { DEMO_USERS } from "../../lib/config";
import {
  LayoutDashboard,
  Search,
  BarChart2,
  Cpu,
  FileText,
  Activity,
  Sun,
  Moon
} from "./Icons";

export type MainSection =
  | "overview"
  | "search_intel"
  | "competitor_intel"
  | "simulation"
  | "content_studio"
  | "system_health";

export const SECTION_SUBTABS: Record<MainSection, { key: string; label: string }[]> = {
  overview: [],
  search_intel: [],
  competitor_intel: [],
  simulation: [],
  content_studio: [],
  system_health: [],
};

const SECTION_CONFIG = [
  { id: "overview",          label: "Overview",                icon: LayoutDashboard },
  { id: "search_intel",      label: "Search & Keywords",       icon: Search },
  { id: "competitor_intel",  label: "Competitor Intelligence", icon: BarChart2 },
  { id: "simulation",        label: "AI Visibility",           icon: Cpu },
  { id: "content_studio",    label: "Content Optimizer",       icon: FileText },
  { id: "system_health",     label: "Execution & Health",      icon: Activity },
];

interface SidebarProps {
  userId: string;
  setUserId: (id: string) => void;
  projects: any[];
  selectedProjectId: string | null;
  onSelectProject: (id: string) => void;
  onDeleteProject: (id: string) => void;
  onCreateProject: (name: string, url: string) => void;
  activeSection: MainSection;
  activeSubTab: string;
  onSectionChange: (section: MainSection, subTab: string) => void;
  onCommandPaletteOpen: () => void;
  isMobileOpen: boolean;
  onMobileClose: () => void;
}

export function Sidebar({
  userId,
  setUserId,
  projects,
  selectedProjectId,
  onSelectProject,
  onDeleteProject,
  onCreateProject,
  activeSection,
  activeSubTab,
  onSectionChange,
  onCommandPaletteOpen,
  isMobileOpen,
  onMobileClose,
}: SidebarProps) {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newUrl, setNewUrl] = useState("");

  const [isDark, setIsDark] = useState(false);

  React.useEffect(() => {
    if (typeof window !== "undefined") {
      setIsDark(document.documentElement.classList.contains("dark"));
    }
  }, []);

  const toggleTheme = () => {
    const nextDark = !isDark;
    setIsDark(nextDark);
    if (typeof window !== "undefined") {
      if (nextDark) {
        document.documentElement.classList.add("dark");
        localStorage.setItem("theme", "dark");
      } else {
        document.documentElement.classList.remove("dark");
        localStorage.setItem("theme", "light");
      }
    }
  };

  const handleSectionClick = (section: MainSection) => {
    onSectionChange(section, "");
    onMobileClose();
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim() || !newUrl.trim()) return;
    onCreateProject(newName.trim(), newUrl.trim());
    setNewName("");
    setNewUrl("");
    setShowCreateForm(false);
  };

  const handleDeleteClick = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    onDeleteProject(id);
  };

  return (
    <>
      {/* Mobile overlay */}
      {isMobileOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.6)",
            zIndex: 99,
            backdropFilter: "blur(2px)",
          }}
          onClick={onMobileClose}
        />
      )}

      <aside className={`sidebar ${isMobileOpen ? "open" : ""}`}>
        {/* Brand Header with Theme Toggle */}
        <div className="sidebar-brand" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div className="flex items-center gap-2">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="url(#brandGrad)" strokeWidth="2.5">
              <defs>
                <linearGradient id="brandGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="var(--primary)" />
                  <stop offset="100%" stopColor="var(--secondary)" />
                </linearGradient>
              </defs>
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
            <span style={{ fontFamily: "var(--font-title)", fontWeight: 600, fontSize: "1.1rem", color: "var(--text-primary)" }}>GeoPilot</span>
          </div>
          <button
            onClick={toggleTheme}
            className="btn btn-ghost btn-icon"
            style={{ width: 28, height: 28, padding: 0, border: "none", cursor: "pointer", background: "none", color: "var(--text-primary)" }}
            aria-label="Toggle theme"
          >
            {isDark ? <Sun /> : <Moon />}
          </button>
        </div>

        {/* Search trigger */}
        <div style={{ padding: "0.75rem 0.75rem 0" }}>
          <button
            className="btn btn-secondary"
            style={{ width: "100%", justifyContent: "flex-start", gap: "0.625rem", fontSize: "0.8125rem" }}
            onClick={onCommandPaletteOpen}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
            </svg>
            <span style={{ color: "var(--text-muted)", flex: 1, textAlign: "left" }}>Search...</span>
            <kbd style={{ fontSize: "0.65rem" }}>⌘K</kbd>
          </button>
        </div>

        <div className="sidebar-divider" style={{ margin: "0.875rem 1rem" }} />

        {/* Workspace Switcher */}
        <div style={{ padding: "0 0.75rem" }}>
          <div className="sidebar-section-header">Workspace</div>
          <select
            className="form-input"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            style={{ fontSize: "0.8125rem", padding: "0.45rem 2rem 0.45rem 0.625rem" }}
          >
            {DEMO_USERS.map((u) => (
              <option key={u.id} value={u.id}>{u.label}</option>
            ))}
          </select>
        </div>

        <div className="sidebar-divider" />

        {/* 6-Section Navigation */}
        <nav style={{ flexShrink: 0 }}>
          <div className="sidebar-section-header">Navigation</div>
          {SECTION_CONFIG.map((section) => {
            const isActive = activeSection === section.id;
            const Icon = section.icon;
            return (
              <button
                key={section.id}
                className={`sidebar-nav-item ${isActive ? "active" : ""}`}
                onClick={() => handleSectionClick(section.id as MainSection)}
                style={{ fontFamily: "var(--font-body)", fontSize: "14px", fontWeight: 500 }}
              >
                <span className="nav-icon"><Icon width="16" height="16" /></span>
                <span style={{ flex: 1 }}>{section.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-divider" />

        {/* Projects */}
        <div style={{ padding: "0 0.75rem", marginBottom: "0.75rem" }}>
          <div className="flex items-center justify-between" style={{ marginBottom: "0.5rem" }}>
            <span className="sidebar-section-header" style={{ margin: 0 }}>
              Projects ({projects.length})
            </span>
            <button
              className="btn-icon btn btn-ghost"
              style={{ width: 24, height: 24, fontSize: "1.1rem", lineHeight: 1 }}
              onClick={() => setShowCreateForm((v) => !v)}
              title="New Project"
              aria-label="Create new project"
            >
              +
            </button>
          </div>

          {showCreateForm && (
            <form onSubmit={handleCreateSubmit} style={{ marginBottom: "0.75rem" }}>
              <input
                className="form-input mb-2"
                placeholder="Project name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                style={{ fontSize: "0.8125rem", padding: "0.45rem 0.625rem", marginBottom: "0.5rem" }}
                required
              />
              <input
                className="form-input mb-2"
                type="url"
                placeholder="https://example.com"
                value={newUrl}
                onChange={(e) => setNewUrl(e.target.value)}
                style={{ fontSize: "0.8125rem", padding: "0.45rem 0.625rem", marginBottom: "0.5rem" }}
                required
              />
              <div className="flex gap-2">
                <button type="submit" className="btn btn-primary btn-sm" style={{ flex: 1, fontSize: "0.75rem" }}>
                  Create
                </button>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShowCreateForm(false)} style={{ fontSize: "0.75rem" }}>
                  Cancel
                </button>
              </div>
            </form>
          )}

          <ul className="sidebar-project-list" style={{ maxHeight: "220px", overflowY: "auto" }}>
            {projects.map((proj) => (
              <li key={proj.id}>
                <div
                  className={`sidebar-project-item ${selectedProjectId === proj.id ? "active" : ""}`}
                  onClick={() => { onSelectProject(proj.id); onMobileClose(); }}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && onSelectProject(proj.id)}
                >
                  <div style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {proj.project_name}
                  </div>
                  <button
                    aria-label={`Delete ${proj.project_name}`}
                    style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-dark)", padding: "0.1rem 0.25rem", borderRadius: 4, lineHeight: 1, flexShrink: 0 }}
                    onClick={(e) => handleDeleteClick(e, proj.id)}
                    onMouseEnter={(e) => (e.currentTarget.style.color = "var(--accent-red)")}
                    onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-dark)")}
                  >
                    ×
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </>
  );
}
