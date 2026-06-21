"use client";

import PaginationControls from "./PaginationControls";

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
            placeholder="Search keywords by text..."
            value={keywordSearch}
            onChange={(e) => onSearchChange(e.target.value)}
            className="form-input"
            style={{ padding: "0.4rem 0.8rem", borderRadius: "6px" }}
          />
        </div>
        <div>
          <select
            value={keywordClusterFilter}
            onChange={(e) => onClusterFilterChange(e.target.value)}
            className="form-input"
            style={{ padding: "0.4rem 0.8rem", borderRadius: "6px" }}
          >
            <option value="All">All Categories</option>
            {keywordsCategories?.map((cat: string) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>
        <div>
          <select
            value={`${keywordsSortBy}-${keywordsSortOrder}`}
            onChange={(e) => {
              const [by, order] = e.target.value.split("-");
              onSortChange(by, order);
            }}
            className="form-input"
            style={{ padding: "0.4rem 0.8rem", borderRadius: "6px" }}
          >
            <option value="keyword-asc">Keyword (A-Z)</option>
            <option value="keyword-desc">Keyword (Z-A)</option>
            <option value="confidence_score-desc">Confidence (High to Low)</option>
            <option value="priority-desc">Priority (High to Low)</option>
          </select>
        </div>
      </div>

      {/* Content */}
      {keywordsLoading ? (
        <div className="card flex-center" style={{ padding: "4rem" }}>
          <div className="spinner"></div>
          <p style={{ color: "var(--text-muted)", marginTop: "1rem" }}>
            Loading semantic keywords...
          </p>
        </div>
      ) : (
        <>
          <div className="table-container">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Keyword Text</th>
                  <th>Category</th>
                  <th>Search Intent</th>
                  <th>Theme Cluster</th>
                  <th>Priority</th>
                  <th>Difficulty</th>
                  <th>Opportunity</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {keywordsData.length > 0 ? (
                  keywordsData.map((kw: any, i: number) => (
                    <tr key={i}>
                      <td>
                        <strong>{kw.keyword_text}</strong>
                      </td>
                      <td>
                        <span className="badge badge-info">{kw.category}</span>
                      </td>
                      <td>
                        <span className="badge badge-success">
                          {kw.search_intent}
                        </span>
                      </td>
                      <td style={{ color: "var(--text-muted)" }}>
                        {kw.clustering_theme || "General"}
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            kw.priority === "High"
                              ? "badge-danger"
                              : kw.priority === "Medium"
                              ? "badge-warning"
                              : "badge-info"
                          }`}
                          style={{ fontSize: "0.75rem" }}
                        >
                          {kw.priority}
                        </span>
                      </td>
                      <td>
                        <span
                          style={{
                            color:
                              kw.difficulty_estimate === "Hard"
                                ? "var(--accent-red)"
                                : kw.difficulty_estimate === "Medium"
                                ? "var(--accent-amber)"
                                : "var(--accent-green)",
                            fontWeight: 600,
                          }}
                        >
                          {kw.difficulty_estimate || "Medium"}
                        </span>
                      </td>
                      <td>
                        <span
                          style={{
                            color:
                              kw.opportunity_estimate === "High"
                                ? "var(--accent-green)"
                                : "var(--text-muted)",
                          }}
                        >
                          {kw.opportunity_estimate || "Medium"}
                        </span>
                      </td>
                      <td>
                        <span
                          className="badge badge-info"
                          style={{
                            background: "rgba(110, 0, 255, 0.1)",
                            color: "var(--primary)",
                            fontSize: "0.75rem",
                          }}
                        >
                          {kw.source || "Discovery"}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td
                      colSpan={8}
                      style={{
                        textAlign: "center",
                        color: "var(--text-dark)",
                      }}
                    >
                      No keywords found matching these criteria.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <PaginationControls
            page={keywordsPage}
            totalCount={keywordsTotalCount}
            loading={keywordsLoading}
            onPrev={onPrevPage}
            onNext={onNextPage}
            label="keywords"
          />
        </>
      )}
    </div>
  );
}
