"use client";

import { useState } from "react";
import PaginationControls from "./PaginationControls";
import { SkeletonCardGrid, NoDataState } from "./ui/SkeletonLoader";
import { ProgressBar, getScoreColor } from "./ui/RadialGauge";

interface KeywordIntelligenceTabProps {
  keywordsData: any[];
  keywordsTotalCount: number;
  keywordsPage: number;
  keywordsLoading: boolean;
  keywordSearch: string;
  keywordClusterFilter: string;
  keywordsSortBy: string;
  keywordsSortOrder: string;
  keywordsCategories: string[];
  onSearchChange: (val: string) => void;
  onClusterFilterChange: (val: string) => void;
  onSortChange: (sortBy: string, sortOrder: string) => void;
  onPrevPage: () => void;
  onNextPage: () => void;
}

const DIFFICULTY_COLOR: Record<string, string> = {
  Hard: "var(--accent-red)",
  Medium: "var(--accent-amber)",
  Easy: "var(--accent-green)",
};

const INTENT_BADGE: Record<string, string> = {
  informational: "badge-info",
  transactional: "badge-success",
  navigational: "badge-purple",
  commercial: "badge-warning",
};

function highlight(text: string, search: string) {
  if (!search.trim()) return <>{text}</>;
  const parts = text.split(new RegExp(`(${search.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi"));
  return (
    <>
      {parts.map((part, i) =>
        part.toLowerCase() === search.toLowerCase() ? (
          <mark key={i} style={{ background: "rgba(139,92,246,0.3)", color: "inherit", borderRadius: "2px", padding: "0 2px" }}>
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}

function KeywordCard({ kw, search }: { kw: any; search: string }) {
  const [expanded, setExpanded] = useState(false);
  const confidence = Math.round((kw.confidence_score ?? 0) * 100);
  const confColor = getScoreColor(confidence);
  const diffColor = DIFFICULTY_COLOR[kw.difficulty_estimate] ?? "var(--text-muted)";
  const intentClass = INTENT_BADGE[kw.search_intent?.toLowerCase()] ?? "badge-muted";

  return (
    <div
      className="card card-interactive"
      style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}
      onClick={() => setExpanded((v) => !v)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && setExpanded((v) => !v)}
      aria-expanded={expanded}
    >
      {/* Top row: keyword + badges */}
      <div className="flex items-start justify-between gap-2">
        <h3 style={{ fontSize: "0.9375rem", fontWeight: 600, flex: 1, minWidth: 0, lineHeight: 1.4 }}>
          {highlight(kw.keyword_text, search)}
        </h3>
        <div className="flex gap-2 flex-wrap" style={{ flexShrink: 0 }}>
          <span className={`badge ${kw.priority === "High" ? "badge-danger" : kw.priority === "Medium" ? "badge-warning" : "badge-info"}`}>
            {kw.priority}
          </span>
          <span className={`badge ${intentClass}`} style={{ textTransform: "capitalize" }}>
            {kw.search_intent ?? "informational"}
          </span>
        </div>
      </div>

      {/* Cluster + category chips */}
      <div className="flex gap-2 flex-wrap">
        {kw.category && <span className="badge badge-muted">{kw.category}</span>}
        {kw.clustering_theme && kw.clustering_theme !== kw.category && (
          <span className="badge badge-muted" style={{ color: "var(--accent-purple)" }}>
            {kw.clustering_theme}
          </span>
        )}
        {kw.source && (
          <span className="badge badge-muted" style={{ color: "var(--primary)" }}>
            {kw.source}
          </span>
        )}
      </div>

      {/* Confidence bar */}
      <div>
        <div className="flex justify-between mb-1">
          <span style={{ fontSize: "0.72rem", color: "var(--text-dark)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Confidence
          </span>
          <span style={{ fontSize: "0.75rem", color: confColor, fontWeight: 600 }}>{confidence}%</span>
        </div>
        <ProgressBar value={confidence} color={confColor} height={4} />
      </div>

      {/* Difficulty + Opportunity row */}
      <div className="flex justify-between" style={{ fontSize: "0.8125rem" }}>
        <div>
          <span style={{ color: "var(--text-dark)", marginRight: 6 }}>Difficulty:</span>
          <span style={{ color: diffColor, fontWeight: 600 }}>{kw.difficulty_estimate ?? "Medium"}</span>
        </div>
        <div>
          <span style={{ color: "var(--text-dark)", marginRight: 6 }}>Opportunity:</span>
          <span style={{ color: kw.opportunity_estimate === "High" ? "var(--accent-green)" : "var(--text-muted)", fontWeight: 500 }}>
            {kw.opportunity_estimate ?? "Medium"}
          </span>
        </div>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div
          className="animate-fade-in"
          style={{
            borderTop: "1px solid var(--border-color)",
            paddingTop: "0.875rem",
            display: "flex",
            flexDirection: "column",
            gap: "0.5rem",
            fontSize: "0.8125rem",
          }}
        >
          {kw.rationale && (
            <p style={{ color: "var(--text-muted)", margin: 0 }}>
              <span style={{ color: "var(--text-dark)", marginRight: 4 }}>Rationale:</span>
              {kw.rationale}
            </p>
          )}
          {kw.target_page_type && (
            <p style={{ color: "var(--text-muted)", margin: 0 }}>
              <span style={{ color: "var(--text-dark)", marginRight: 4 }}>Target Page:</span>
              {kw.target_page_type}
            </p>
          )}
        </div>
      )}

      {/* Expand hint */}
      <div style={{ textAlign: "right", marginTop: -4 }}>
        <svg
          width="12" height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="var(--text-dark)"
          strokeWidth="2"
          style={{ transition: "transform 0.2s", transform: expanded ? "rotate(180deg)" : "rotate(0deg)" }}
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </div>
    </div>
  );
}

export default function KeywordIntelligenceTab({
  keywordsData,
  keywordsTotalCount,
  keywordsPage,
  keywordsLoading,
  keywordSearch,
  keywordClusterFilter,
  keywordsSortBy,
  keywordsSortOrder,
  keywordsCategories,
  onSearchChange,
  onClusterFilterChange,
  onSortChange,
  onPrevPage,
  onNextPage,
}: KeywordIntelligenceTabProps) {
  return (
    <div className="animate-fade-in">
      {/* Toolbar */}
      <div
        className="card"
        style={{ padding: "0.875rem 1rem", marginBottom: "1.25rem", display: "flex", gap: "0.875rem", flexWrap: "wrap", alignItems: "center" }}
      >
        {/* Search */}
        <div style={{ flex: 1, minWidth: "200px", position: "relative" }}>
          <svg
            width="14" height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--text-dark)"
            strokeWidth="2"
            style={{ position: "absolute", left: "0.75rem", top: "50%", transform: "translateY(-50%)" }}
          >
            <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
          </svg>
          <input
            type="text"
            placeholder="Search keywords..."
            value={keywordSearch}
            onChange={(e) => onSearchChange(e.target.value)}
            className="form-input"
            style={{ paddingLeft: "2.25rem" }}
            aria-label="Search keywords"
          />
        </div>

        {/* Category filter */}
        <select
          value={keywordClusterFilter}
          onChange={(e) => onClusterFilterChange(e.target.value)}
          className="form-input"
          style={{ minWidth: "160px" }}
          aria-label="Filter by category"
        >
          <option value="All">All Categories</option>
          {keywordsCategories?.map((cat) => <option key={cat} value={cat}>{cat}</option>)}
        </select>

        {/* Sort */}
        <select
          value={`${keywordsSortBy}-${keywordsSortOrder}`}
          onChange={(e) => {
            const [by, order] = e.target.value.split("-");
            onSortChange(by, order);
          }}
          className="form-input"
          style={{ minWidth: "200px" }}
          aria-label="Sort keywords"
        >
          <option value="keyword-asc">Keyword (A → Z)</option>
          <option value="keyword-desc">Keyword (Z → A)</option>
          <option value="confidence_score-desc">Confidence (High → Low)</option>
          <option value="priority-desc">Priority (High → Low)</option>
        </select>

        {/* Count */}
        <div style={{ color: "var(--text-dark)", fontSize: "0.8125rem", whiteSpace: "nowrap" }}>
          <strong style={{ color: "var(--text-muted)" }}>{keywordsTotalCount}</strong> keywords
        </div>
      </div>

      {/* Content */}
      {keywordsLoading ? (
        <SkeletonCardGrid count={6} />
      ) : keywordsData.length === 0 ? (
        <NoDataState
          title="No keywords found"
          description="Try adjusting filters or run an analysis to discover semantic keywords."
        />
      ) : (
        <>
          <div className="card-grid">
            {keywordsData.map((kw, i) => (
              <KeywordCard key={kw.id ?? i} kw={kw} search={keywordSearch} />
            ))}
          </div>

          <div style={{ marginTop: "1.25rem" }}>
            <PaginationControls
              page={keywordsPage}
              totalCount={keywordsTotalCount}
              loading={keywordsLoading}
              onPrev={onPrevPage}
              onNext={onNextPage}
              label="keywords"
            />
          </div>
        </>
      )}
    </div>
  );
}
