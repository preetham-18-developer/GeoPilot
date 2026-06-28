"use client";

import { useState } from "react";
import PaginationControls from "./PaginationControls";
import { SkeletonCardGrid, NoDataState } from "./ui/SkeletonLoader";
import { ProgressBar, getScoreColor } from "./ui/RadialGauge";

interface QuestionDiscoveryTabProps {
  questionsData: any[];
  questionsTotalCount: number;
  questionsPage: number;
  questionsLoading: boolean;
  questionSearch: string;
  questionTypeFilter: string;
  questionsSortBy: string;
  questionsSortOrder: string;
  questionsCategories: string[];
  onSearchChange: (val: string) => void;
  onTypeFilterChange: (val: string) => void;
  onSortChange: (sortBy: string, sortOrder: string) => void;
  onPrevPage: () => void;
  onNextPage: () => void;
}

function highlight(text: string, query: string) {
  if (!query.trim() || !text) return <>{text}</>;
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const parts = text.split(new RegExp(`(${escaped})`, "gi"));
  return (
    <>
      {parts.map((p, i) =>
        p.toLowerCase() === query.toLowerCase() ? (
          <mark key={i} style={{ background: "rgba(139,92,246,0.35)", color: "inherit", borderRadius: "2px", padding: "0 2px" }}>
            {p}
          </mark>
        ) : (
          <span key={i}>{p}</span>
        )
      )}
    </>
  );
}

function QuestionCard({ q, search }: { q: any; search: string }) {
  const [expanded, setExpanded] = useState(false);
  const priority_score = q.priority_score ?? 0;
  const rec_score = q.recommendation_score ?? 0;
  const confidence = Math.round((q.confidence_score ?? 0) * 100);

  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: "0.875rem" }}>
      {/* Header: category + priority */}
      <div className="flex items-center justify-between gap-2">
        <span className="badge badge-info" style={{ fontSize: "0.7rem" }}>{q.category ?? "General"}</span>
        <div className="flex gap-2">
          <span className={`badge ${q.priority === "High" ? "badge-danger" : q.priority === "Medium" ? "badge-warning" : "badge-muted"}`} style={{ fontSize: "0.7rem" }}>
            {q.priority ?? "Low"} Priority
          </span>
          <span className="badge badge-muted" style={{ fontSize: "0.7rem", textTransform: "capitalize" }}>
            {q.intent ?? "informational"}
          </span>
        </div>
      </div>

      {/* Question text */}
      <h3
        style={{ fontSize: "0.9375rem", fontWeight: 600, lineHeight: 1.5, color: "var(--text-main)", margin: 0, cursor: "pointer" }}
        onClick={() => setExpanded((v) => !v)}
      >
        {highlight(q.question_text, search)}
      </h3>

      {/* Score bars */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        <ProgressBar value={rec_score} label="Recommendation" showLabel color={getScoreColor(rec_score)} height={4} />
        <ProgressBar value={priority_score} label="Priority" showLabel color="var(--accent-amber)" height={4} />
        <ProgressBar value={confidence} label="Confidence" showLabel color="var(--secondary)" height={4} />
      </div>

      {/* Metadata chips */}
      <div className="flex gap-2 flex-wrap" style={{ fontSize: "0.75rem" }}>
        <span style={{ color: "var(--text-dark)" }}>
          Difficulty:{" "}
          <span style={{
            fontWeight: 600,
            color: q.difficulty_estimate === "Hard" ? "var(--accent-red)" : q.difficulty_estimate === "Medium" ? "var(--accent-amber)" : "var(--accent-green)"
          }}>
            {q.difficulty_estimate ?? "Medium"}
          </span>
        </span>
        <span style={{ color: "var(--border-strong)" }}>·</span>
        <span style={{ color: "var(--text-dark)" }}>
          Opportunity:{" "}
          <span style={{ fontWeight: 600, color: q.opportunity_estimate === "High" ? "var(--accent-green)" : "var(--text-muted)" }}>
            {q.opportunity_estimate ?? "Medium"}
          </span>
        </span>
        <span style={{ color: "var(--border-strong)" }}>·</span>
        <span style={{ color: "var(--text-dark)" }}>
          Commercial: <span style={{ fontWeight: 600, color: "var(--primary)" }}>{q.commercial_score ?? 0}/100</span>
        </span>
      </div>

      {/* Expandable answer */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="btn btn-ghost btn-sm"
        style={{ justifyContent: "flex-start", gap: "0.5rem", paddingLeft: 0 }}
        aria-expanded={expanded}
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          style={{ transition: "transform 0.2s", transform: expanded ? "rotate(90deg)" : "rotate(0deg)" }}>
          <path d="m9 18 6-6-6-6" />
        </svg>
        {expanded ? "Hide" : "Show"} recommended answer
      </button>

      {expanded && q.recommended_answer && (
        <div
          className="animate-fade-in"
          style={{
            borderLeft: "2px solid var(--secondary)",
            paddingLeft: "1rem",
            fontSize: "0.8375rem",
            color: "var(--text-muted)",
            lineHeight: 1.65,
          }}
        >
          {q.recommended_answer}
        </div>
      )}
    </div>
  );
}

export default function QuestionDiscoveryTab({
  questionsData,
  questionsTotalCount,
  questionsPage,
  questionsLoading,
  questionSearch,
  questionTypeFilter,
  questionsSortBy,
  questionsSortOrder,
  questionsCategories,
  onSearchChange,
  onTypeFilterChange,
  onSortChange,
  onPrevPage,
  onNextPage,
}: QuestionDiscoveryTabProps) {
  return (
    <div className="animate-fade-in">
      {/* Toolbar */}
      <div className="card" style={{ padding: "0.875rem 1rem", marginBottom: "1.25rem", display: "flex", gap: "0.875rem", flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ flex: 1, minWidth: "200px", position: "relative" }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-dark)" strokeWidth="2"
            style={{ position: "absolute", left: "0.75rem", top: "50%", transform: "translateY(-50%)" }}>
            <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
          </svg>
          <input
            type="text"
            placeholder="Search questions..."
            value={questionSearch}
            onChange={(e) => onSearchChange(e.target.value)}
            className="form-input"
            style={{ paddingLeft: "2.25rem" }}
            aria-label="Search questions"
          />
        </div>

        <select
          value={questionTypeFilter}
          onChange={(e) => onTypeFilterChange(e.target.value)}
          className="form-input"
          style={{ minWidth: "160px" }}
          aria-label="Filter by category"
        >
          <option value="All">All Categories</option>
          {questionsCategories?.map((cat) => <option key={cat} value={cat}>{cat}</option>)}
        </select>

        <select
          value={`${questionsSortBy}-${questionsSortOrder}`}
          onChange={(e) => {
            const [by, order] = e.target.value.split("-");
            onSortChange(by, order);
          }}
          className="form-input"
          style={{ minWidth: "220px" }}
          aria-label="Sort questions"
        >
          <option value="priority_score-desc">Priority Score (High → Low)</option>
          <option value="recommendation_score-desc">Recommendation Score (High → Low)</option>
          <option value="commercial_score-desc">Commercial Score (High → Low)</option>
          <option value="question-asc">Question Text (A → Z)</option>
          <option value="confidence_score-desc">Confidence Score (High → Low)</option>
        </select>

        <div style={{ color: "var(--text-dark)", fontSize: "0.8125rem", whiteSpace: "nowrap" }}>
          <strong style={{ color: "var(--text-muted)" }}>{questionsTotalCount}</strong> queries
        </div>
      </div>

      {/* Content */}
      {questionsLoading ? (
        <SkeletonCardGrid count={6} />
      ) : questionsData.length === 0 ? (
        <NoDataState
          title="No questions found"
          description="Try adjusting your search or filters. Run an analysis to discover LLM queries."
        />
      ) : (
        <>
          <div className="card-grid">
            {questionsData.map((q, i) => (
              <QuestionCard key={q.id ?? i} q={q} search={questionSearch} />
            ))}
          </div>
          <div style={{ marginTop: "1.25rem" }}>
            <PaginationControls
              page={questionsPage}
              totalCount={questionsTotalCount}
              loading={questionsLoading}
              onPrev={onPrevPage}
              onNext={onNextPage}
              label="queries"
            />
          </div>
        </>
      )}
    </div>
  );
}
