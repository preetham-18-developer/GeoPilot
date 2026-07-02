"use client";

import { useState, useEffect } from "react";
import { API_BASE } from "../lib/api";

interface Question {
  id?: string;
  question?: string;
  question_text?: string;
  category?: string;
  question_type?: string;
  priority_score?: number;
}

interface QuestionsTableProps {
  projectId: string;
  userId: string;
}

const PAGE_SIZE = 50;

const CATEGORIES = [
  "All",
  "DIRECT",
  "PROBLEM",
  "COMPARISON",
  "VOICE",
  "AI_RECOMMENDATION",
];

const categoryColors: Record<string, { bg: string; text: string }> = {
  DIRECT:            { bg: "#EEF2FF", text: "#4F46E5" },
  PROBLEM:           { bg: "#FFF1F2", text: "#E11D48" },
  COMPARISON:        { bg: "#FFFBEB", text: "#D97706" },
  VOICE:             { bg: "#F0FDF4", text: "#059669" },
  AI_RECOMMENDATION: { bg: "#F5F3FF", text: "#7C3AED" },
};

function getToken(): string {
  if (typeof window === "undefined") return "";
  return (
    localStorage.getItem("token") ||
    localStorage.getItem("access_token") ||
    sessionStorage.getItem("token") ||
    ""
  );
}

export function QuestionsTable({ projectId, userId }: QuestionsTableProps) {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) {
      console.warn("[QuestionsTable] No projectId provided — skipping fetch");
      return;
    }

    const fetchQuestions = async () => {
      setLoading(true);
      setError(null);

      const token = getToken();

      const params = new URLSearchParams({
        page: String(page),
        page_size: String(PAGE_SIZE),
        sort_by: "priority_score",
        sort_order: "desc",
      });
      if (search) params.set("search", search);
      if (category && category !== "All") params.set("question_type", category);

      // === DEBUG LOGS — remove after confirming working ===
      console.log("=== QUESTIONS FETCH DEBUG ===");
      console.log("Project ID:", projectId);
      console.log("Token:", token ? token.slice(0, 20) + "..." : "MISSING ⚠️");
      console.log("API Base:", API_BASE);
      // =====================================================

      // Try both URL patterns; whichever returns 200 wins
      const urls = [
        `${API_BASE}/api/v1/projects/${projectId}/questions?${params}`,
        `${API_BASE}/api/v1/analysis/questions/${projectId}?${params}`,
      ];

      let lastError = "";

      for (const url of urls) {
        try {
          console.log("[Questions] Trying:", url);

          const response = await fetch(url, {
            headers: {
              "Content-Type": "application/json",
              Authorization: token ? `Bearer ${token}` : "",
            },
          });

          console.log("[Questions] Status:", response.status);

          // Auto-logout on expired session
          if (response.status === 401) {
            console.warn("[Questions] 401 — session expired, redirecting to /login");
            localStorage.removeItem("token");
            localStorage.removeItem("access_token");
            window.location.href = "/login";
            return;
          }

          if (response.ok) {
            const data = await response.json();
            console.log("[Questions] Data keys:", Object.keys(data));

            const items: Question[] =
              data.questions || data.items || data.data || data.results || [];
            const count: number =
              data.total ?? data.count ?? data.total_count ?? items.length;

            setQuestions(items);
            setTotal(count);
            setLoading(false);
            return; // success — stop trying
          }

          lastError = `HTTP ${response.status} from ${url}`;
          console.warn("[Questions] Non-OK status:", response.status, "— trying next URL");
        } catch (err: any) {
          lastError = err.message;
          console.error("[Questions] Fetch error:", err.message);
        }
      }

      // Both URLs failed
      setError(`Failed to load questions: ${lastError}`);
      setLoading(false);
    };

    fetchQuestions();
  }, [projectId, page, search, category]);

  // ── No project guard ──────────────────────────────────────────────────────
  if (!projectId) {
    return (
      <div
        style={{
          padding: "40px",
          textAlign: "center",
          color: "var(--text-muted)",
          background: "var(--bg-card)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-lg)",
        }}
      >
        Select a project to view questions.
      </div>
    );
  }

  const categoryColor = (cat: string) =>
    categoryColors[cat] || { bg: "var(--bg-card-hover)", text: "var(--text-muted)" };

  const exportCSV = () => {
    const headers = ["Question", "Category"];
    const rows = questions.map((q) => [
      q.question_text || q.question || "",
      q.question_type || q.category || "GENERAL",
    ]);
    const csvContent =
      "data:text/csv;charset=utf-8," +
      [
        headers.join(","),
        ...rows.map((e) =>
          e.map((val) => `"${String(val).replace(/"/g, '""')}"`).join(",")
        ),
      ].join("\n");
    const link = document.createElement("a");
    link.href = encodeURI(csvContent);
    link.download = `questions_project_${projectId}_${Date.now()}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div
      className="card animate-fade-in"
      style={{
        padding: "24px",
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      {/* Header */}
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
        <button
          className="btn btn-secondary btn-sm"
          onClick={exportCSV}
          disabled={questions.length === 0}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            style={{ marginRight: "4px" }}
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
          </svg>
          Export CSV
        </button>
      </div>

      {/* Filters */}
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
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="form-input"
            style={{ width: "100%", paddingLeft: "2.25rem", boxSizing: "border-box" }}
          />
        </div>
        <select
          value={category}
          onChange={(e) => { setCategory(e.target.value); setPage(1); }}
          className="form-input"
          style={{ padding: "10px 16px", background: "var(--bg-card)", cursor: "pointer", minWidth: "160px" }}
        >
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c === "All" ? "All Categories" : c}
            </option>
          ))}
        </select>
      </div>

      {/* States */}
      {loading && (
        <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
          Loading questions...
        </div>
      )}

      {error && (
        <div
          style={{
            padding: "20px",
            background: "#FFF1F2",
            border: "1px solid #FECDD3",
            borderRadius: "8px",
            marginBottom: "16px",
          }}
        >
          <p style={{ color: "#E11D48", margin: 0, fontWeight: 600 }}>
            Failed to load questions
          </p>
          <p style={{ color: "var(--text-muted)", fontSize: "14px", marginBottom: "12px" }}>
            {error}
          </p>
          <button
            className="btn btn-primary btn-sm"
            onClick={() => setPage((p) => p)}
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !error && questions.length === 0 && (
        <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
          <p style={{ fontSize: "16px", marginBottom: "8px" }}>No questions found</p>
          <p style={{ fontSize: "13px" }}>
            Run an analysis to discover questions for this project.
          </p>
        </div>
      )}

      {/* Table */}
      {!loading && questions.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
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
                const cat = q.question_type || q.category || "";
                const colors = categoryColor(cat);
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
                      {cat && (
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
                          {cat}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {total > PAGE_SIZE && (
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
            Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of{" "}
            {total.toLocaleString()}
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
              Page {page} of {Math.ceil(total / PAGE_SIZE)}
            </span>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setPage((p) => p + 1)}
              disabled={page * PAGE_SIZE >= total}
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
