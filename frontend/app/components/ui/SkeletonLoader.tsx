"use client";

import React from "react";

// ─── Skeleton Components ──────────────────────────────────────

export function SkeletonText({ width = "100%", className = "" }: { width?: string; className?: string }) {
  return (
    <div
      className={`skeleton skeleton-text ${className}`}
      style={{ width }}
      aria-hidden="true"
    />
  );
}

export function SkeletonTitle({ width = "60%" }: { width?: string }) {
  return (
    <div
      className="skeleton skeleton-title"
      style={{ width }}
      aria-hidden="true"
    />
  );
}

export function SkeletonCard({ height = 120 }: { height?: number }) {
  return (
    <div
      className="skeleton skeleton-card"
      style={{ height }}
      aria-hidden="true"
    />
  );
}

export function SkeletonStatCard() {
  return (
    <div className="stat-card" aria-hidden="true">
      <SkeletonText width="40%" />
      <div className="skeleton" style={{ height: "2rem", width: "60%", borderRadius: 8, marginTop: 6 }} />
      <SkeletonText width="30%" />
    </div>
  );
}

export function SkeletonCardGrid({ count = 3 }: { count?: number }) {
  return (
    <div className="grid-3" aria-busy="true" aria-label="Loading...">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonStatCard key={i} />
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="table-container" aria-busy="true" aria-label="Loading...">
      <div style={{ padding: "0.875rem 1rem", borderBottom: "1px solid var(--border-color)" }}>
        <div className="flex gap-4">
          {Array.from({ length: cols }).map((_, i) => (
            <div key={i} className="skeleton skeleton-text" style={{ flex: 1 }} />
          ))}
        </div>
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          style={{ padding: "0.875rem 1rem", borderBottom: i < rows - 1 ? "1px solid var(--border-color)" : "none" }}
        >
          <div className="flex gap-4">
            {Array.from({ length: cols }).map((_, j) => (
              <div
                key={j}
                className="skeleton skeleton-text"
                style={{ flex: 1, opacity: 0.6 + j * 0.1 }}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function SkeletonDashboard() {
  return (
    <div className="animate-fade-in" aria-busy="true">
      <div className="mb-6">
        <SkeletonTitle width="40%" />
        <SkeletonText width="60%" className="mt-2" />
      </div>
      <SkeletonCardGrid count={4} />
      <div className="mb-6 mt-6">
        <SkeletonCard height={200} />
      </div>
      <div className="grid-2">
        <SkeletonCard height={160} />
        <SkeletonCard height={160} />
      </div>
    </div>
  );
}

// ─── Empty State ──────────────────────────────────────────────

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  compact?: boolean;
}

export function EmptyState({ icon, title, description, action, compact = false }: EmptyStateProps) {
  return (
    <div
      className="empty-state animate-fade-in"
      style={{ padding: compact ? "2rem" : "4rem 2rem" }}
      role="status"
    >
      {icon && <div className="empty-state-icon">{icon}</div>}
      <div className="empty-state-title">{title}</div>
      {description && <p className="empty-state-desc">{description}</p>}
      {action && <div style={{ marginTop: "1rem" }}>{action}</div>}
    </div>
  );
}

export function NoDataState({ title = "No data available", description = "Run an analysis to populate this section." }: { title?: string; description?: string }) {
  return (
    <EmptyState
      icon={
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" width="40" height="40">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 6v6m0 4h.01" />
        </svg>
      }
      title={title}
      description={description}
    />
  );
}

// ─── Error State ──────────────────────────────────────────────

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="error-state animate-fade-in" role="alert">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: "var(--accent-red)", flexShrink: 0 }}>
        <circle cx="12" cy="12" r="10" />
        <path d="M12 8v4m0 4h.01" />
      </svg>
      <div className="flex-1 min-w-0">
        <p className="error-state-message">{message}</p>
        {onRetry && (
          <button
            className="btn btn-sm btn-secondary"
            onClick={onRetry}
            style={{ marginTop: "0.625rem" }}
          >
            Try Again
          </button>
        )}
      </div>
    </div>
  );
}

// ─── Section Header ───────────────────────────────────────────

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  badge?: React.ReactNode;
}

export function SectionHeader({ title, subtitle, actions, badge }: SectionHeaderProps) {
  return (
    <div className="section-header">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3">
          <h2 className="section-title">{title}</h2>
          {badge}
        </div>
        {subtitle && <p className="section-subtitle">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

// ─── Loading Spinner ──────────────────────────────────────────

export function LoadingSpinner({ size = "md", label = "Loading..." }: { size?: "sm" | "md" | "lg"; label?: string }) {
  const cls = size === "lg" ? "spinner spinner-lg" : "spinner";
  return (
    <div className="flex-center flex-col gap-3" role="status" aria-label={label}>
      <div className={cls} />
      <p style={{ color: "var(--text-dark)", fontSize: "0.875rem" }}>{label}</p>
    </div>
  );
}

// ─── Loading Page ─────────────────────────────────────────────

export function LoadingPage({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex-center" style={{ height: "100%", minHeight: "300px", padding: "4rem" }}>
      <LoadingSpinner size="lg" label={label} />
    </div>
  );
}
