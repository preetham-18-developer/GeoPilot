"use client";

import { useState, useEffect } from "react";
import { apiGet, ROUTES } from "../lib/api";

interface Question {
  id?: string;
  question?: string;
  question_text?: string;
  category: string;
}

interface QuestionsTableProps {
  projectId: string;
  userId: string;
}

export function QuestionsTable({ projectId, userId }: QuestionsTableProps) {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const CATEGORIES = [
    "All",
    "DIRECT",
    "PROBLEM",
    "COMPARISON",
    "VOICE",
    "AI_RECOMMENDATION",
  ];

  useEffect(() => {
    if (!projectId) return;

    setLoading(true);
    setError(null);

    const params = new URLSearchParams({
      page: String(page),
      page_size: "50",
      sort_by: "priority_score",
      sort_order: "desc",
    });
    if (search) params.set("search", search);
    if (category && category !== "All") {
      params.set("question_type", category);
    }

    apiGet(`${ROUTES.questions(projectId)}?${params}`)
      .then((data) => {
        if (!data) return;

        // Handle different response shapes
        const questions = data.questions || data.items || data.data || [];
        const total = data.total || data.count || data.total_count || questions.length;

        setQuestions(questions);
        setTotal(total);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Questions fetch error:", err);
        setError(err.message);
        setLoading(false);
      });
  }, [projectId, page, search, category]);

  if (error) return (
    <div style={{ padding: "40px", textAlign: "center", background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)" }}>
      <p style={{ color: "#E11D48", fontWeight: 600 }}>Failed to load questions</p>
      <p style={{ color: "var(--text-muted)", fontSize: "14px", marginBottom: "16px" }}>{error}</p>
      <button className="btn btn-primary btn-sm" onClick={() => window.location.reload()}>
        Retry
      </button>
    </div>
  );

  const categoryColor = (cat: string) => {
    const colors: Record<string, { bg: string; text: string }> = {
      DIRECT: { bg: "#EEF2FF", text: "#4F46E5" },
      PROBLEM: { bg: "#FFF1F2", text: "#E11D48" },
      COMPARISON: { bg: "#FFFBEB", text: "#D97706" },
      VOICE: { bg: "#F0FDF4", text: "#059669" },
      AI_RECOMMENDATION: { bg: "#EEF2FF", text: "#7C3AED" },
    };
    return colors[cat] || { bg: "var(--bg-card-hover)", text: "var(--text-muted)" };
  };

  const exportQuestionsCSV = (qs: Question[]) => {
    const headers = ["Question", "Category"];
    const rows = qs.map((q) => [q.question_text || q.question || "", q.category || "GENERAL"]);
    const csvContent =
      "data:text/csv;charset=utf-8," +
      [
        headers.join(","),
        ...rows.map((e) =>
          e.map((val) => `"${String(val).replace(/"/g, '""')}"`).join(",")
        ),
      ].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `questions_project_${projectId}_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="card animate-fade-in" style={{ padding: "24px", background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "20px",
        }}
      >
        <h2 style={{ margin: 0, fontSize: "1.25rem", color: "var(--text-primary)" }}>
          Questions
          <span
            style={{
              color: "var(--text-muted)",
              fontSize: "14px",
              fontWeight: 400,
              marginLeft: "8px",
            }}
          >
            ({total.toLocaleString()} total)
          </span>
        </h2>
        <button className="btn btn-secondary btn-sm" onClick={() => exportQuestionsCSV(questions)} disabled={questions.length === 0}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: "4px" }}>
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
          </svg>
          Export CSV
        </button>
      </div>

      {/* Filters Row */}
      <div style={{ display: "flex", gap: "12px", marginBottom: "20px", flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: "200px", position: "relative" }}>
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--text-muted)"
            strokeWidth="2"
            style={{ position: "absolute", left: "0.75rem", top: "50%", transform: "translateY(-50%)" }}
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <input
            placeholder="Search questions..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="form-input"
            style={{
              width: "100%",
              paddingLeft: "2.25rem",
              boxSizing: "border-box",
            }}
          />
        </div>
        <select
          value={category}
          onChange={(e) => {
            setCategory(e.target.value);
            setPage(1);
          }}
          className="form-input"
          style={{
            padding: "10px 16px",
            background: "var(--bg-card)",
            cursor: "pointer",
            minWidth: "160px",
          }}
        >
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c === "All" ? "All Categories" : c}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
          Loading questions...
        </div>
      ) : questions.length === 0 ? (
        <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
          No questions found for this filter.
        </div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontSize: "14px",
            }}
          >
            <thead>
              <tr
                style={{
                  background: "var(--bg-card-hover)",
                  borderBottom: "2px solid var(--border)",
                }}
              >
                <th
                  style={{
                    padding: "12px 16px",
                    textAlign: "left",
                    fontWeight: 600,
                    color: "var(--text-muted)",
                    fontSize: "11px",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                  }}
                >
                  Question
                </th>
                <th
                  style={{
                    padding: "12px 16px",
                    textAlign: "left",
                    fontWeight: 600,
                    color: "var(--text-muted)",
                    fontSize: "11px",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    width: "180px",
                  }}
                >
                  Category
                </th>
              </tr>
            </thead>
            <tbody>
              {questions.map((q, index) => {
                const colors = categoryColor(q.category);
                return (
                  <tr
                    key={q.id || index}
                    style={{
                      borderBottom: "1px solid var(--border)",
                      transition: "background var(--transition-fast)",
                    }}
                    className="table-row-hover"
                  >
                    <td
                      style={{
                        padding: "16px",
                        color: "var(--text-primary)",
                        lineHeight: "1.5",
                        fontWeight: 500,
                      }}
                    >
                      {q.question_text || q.question}
                    </td>
                    <td style={{ padding: "16px" }}>
                      <span
                        style={{
                          display: "inline-block",
                          padding: "3px 8px",
                          borderRadius: "4px",
                          fontSize: "11px",
                          fontWeight: 600,
                          background: colors.bg,
                          color: colors.text,
                        }}
                      >
                        {q.category || "GENERAL"}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {total > 50 && (
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginTop: "20px",
            color: "var(--text-muted)",
            fontSize: "14px",
          }}
        >
          <span>
            Showing {((page - 1) * 50 + 1)}-{Math.min(page * 50, total)} of {total.toLocaleString()}
          </span>
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              ← Previous
            </button>
            <span
              style={{
                padding: "6px 12px",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-md)",
                background: "var(--bg-card-hover)",
                fontSize: "0.875rem",
              }}
            >
              Page {page} of {Math.ceil(total / 50)}
            </span>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setPage((p) => p + 1)}
              disabled={page * 50 >= total}
            >
              Next →
            </button>
          </div>
        </div>
      )}

      <style jsx global>{`
        .table-row-hover:hover {
          background: var(--bg-card-hover) !important;
        }
      `}</style>
    </div>
  );
}
