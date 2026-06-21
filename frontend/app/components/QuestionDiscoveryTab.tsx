"use client";

import PaginationControls from "./PaginationControls";

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
    <div>
      {/* Filters */}
      <div
        className="card"
        style={{
          padding: "1rem",
          marginBottom: "1.5rem",
          display: "flex",
          gap: "1rem",
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        <div style={{ flex: 1, minWidth: "200px" }}>
          <input
            type="text"
            placeholder="Search questions by text..."
            value={questionSearch}
            onChange={(e) => onSearchChange(e.target.value)}
            className="form-input"
            style={{ padding: "0.4rem 0.8rem", borderRadius: "6px" }}
          />
        </div>
        <div>
          <select
            value={questionTypeFilter}
            onChange={(e) => onTypeFilterChange(e.target.value)}
            className="form-input"
            style={{ padding: "0.4rem 0.8rem", borderRadius: "6px" }}
          >
            <option value="All">All Categories</option>
            {questionsCategories?.map((cat: string) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>
        <div>
          <select
            value={`${questionsSortBy}-${questionsSortOrder}`}
            onChange={(e) => {
              const [by, order] = e.target.value.split("-");
              onSortChange(by, order);
            }}
            className="form-input"
            style={{ padding: "0.4rem 0.8rem", borderRadius: "6px" }}
          >
            <option value="priority_score-desc">Priority Score (Highest first)</option>
            <option value="recommendation_score-desc">Recommendation Score (Highest first)</option>
            <option value="commercial_score-desc">Commercial Score (Highest first)</option>
            <option value="question-asc">Question Text (A-Z)</option>
            <option value="confidence_score-desc">Confidence Score (Highest first)</option>
          </select>
        </div>
      </div>

      {/* Content */}
      {questionsLoading ? (
        <div className="card flex-center" style={{ padding: "4rem" }}>
          <div className="spinner"></div>
          <p style={{ color: "var(--text-muted)", marginTop: "1rem" }}>
            Loading discovered questions...
          </p>
        </div>
      ) : (
        <>
          <div className="grid-2">
            {questionsData.length > 0 ? (
              questionsData.map((q: any, i: number) => (
                <div
                  key={i}
                  className="card glow-border"
                  style={{ padding: "1.5rem" }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: "0.75rem",
                    }}
                  >
                    <span
                      className="badge badge-success"
                      style={{ fontSize: "0.75rem" }}
                    >
                      {q.category}
                    </span>
                    <span
                      className={`badge ${
                        q.priority === "High"
                          ? "badge-danger"
                          : q.priority === "Medium"
                          ? "badge-warning"
                          : "badge-info"
                      }`}
                      style={{ fontSize: "0.75rem" }}
                    >
                      {q.priority} Priority
                    </span>
                  </div>
                  <h3 style={{ marginBottom: "0.75rem", fontSize: "1.1rem" }}>
                    {q.question_text}
                  </h3>

                  {/* Multi-factor Score Grid */}
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(2, 1fr)",
                      gap: "0.5rem",
                      fontSize: "0.8rem",
                      color: "var(--text-muted)",
                      marginBottom: "1rem",
                      background: "rgba(255,255,255,0.02)",
                      padding: "0.75rem",
                      borderRadius: "8px",
                      border: "1px solid rgba(255,255,255,0.05)",
                    }}
                  >
                    <div>
                      Recommendation:{" "}
                      <strong style={{ color: "var(--accent-green)" }}>
                        {q.recommendation_score ?? 0}/100
                      </strong>
                    </div>
                    <div>
                      Commercial Score:{" "}
                      <strong style={{ color: "var(--secondary)" }}>
                        {q.commercial_score ?? 0}/100
                      </strong>
                    </div>
                    <div>
                      Intent Score: <strong>{q.intent_score ?? 0}/100</strong>
                    </div>
                    <div>
                      Priority Score:{" "}
                      <strong style={{ color: "var(--accent-amber)" }}>
                        {q.priority_score ?? 0}/100
                      </strong>
                    </div>
                    <div>
                      Difficulty:{" "}
                      <span
                        style={{
                          color:
                            q.difficulty_estimate === "Hard"
                              ? "var(--accent-red)"
                              : q.difficulty_estimate === "Medium"
                              ? "var(--accent-amber)"
                              : "var(--accent-green)",
                          fontWeight: 600,
                        }}
                      >
                        {q.difficulty_estimate || "Medium"}
                      </span>
                    </div>
                    <div>
                      Opportunity:{" "}
                      <span
                        style={{
                          color:
                            q.opportunity_estimate === "High"
                              ? "var(--accent-green)"
                              : "var(--text-muted)",
                        }}
                      >
                        {q.opportunity_estimate || "Medium"}
                      </span>
                    </div>
                    <div>
                      Search Intent:{" "}
                      <strong style={{ textTransform: "capitalize" }}>
                        {q.intent || "informational"}
                      </strong>
                    </div>
                    <div>
                      Confidence:{" "}
                      <strong>
                        {(q.confidence_score * 100).toFixed(0)}%
                      </strong>
                    </div>
                  </div>

                  <p
                    style={{
                      fontSize: "0.9rem",
                      color: "var(--text-muted)",
                      borderLeft: "2px solid var(--secondary)",
                      paddingLeft: "1rem",
                      margin: 0,
                    }}
                  >
                    <strong>Optimized Answer Context:</strong>
                    <br />
                    {q.recommended_answer}
                  </p>
                </div>
              ))
            ) : (
              <div
                className="card flex-center"
                style={{ gridColumn: "1 / -1", padding: "4rem" }}
              >
                <p style={{ color: "var(--text-muted)" }}>
                  No questions discovered matching these criteria.
                </p>
              </div>
            )}
          </div>

          <PaginationControls
            page={questionsPage}
            totalCount={questionsTotalCount}
            loading={questionsLoading}
            onPrev={onPrevPage}
            onNext={onNextPage}
            label="queries"
          />
        </>
      )}
    </div>
  );
}
