"use client";

import { useState, useEffect } from "react";
import { API_BASE } from "../lib/api";

interface Keyword {
  id?: string;
  keyword: string;
  keyword_type?: string;
  frequency?: number;
}

interface KeywordsTableProps {
  projectId: string;
  userId: string;
}

const PAGE_SIZE = 50;

function getToken(): string {
  if (typeof window === "undefined") return "";
  return (
    localStorage.getItem("token") ||
    localStorage.getItem("access_token") ||
    sessionStorage.getItem("token") ||
    ""
  );
}

export function KeywordsTable({ projectId, userId }: KeywordsTableProps) {
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) {
      console.warn("[KeywordsTable] No projectId provided — skipping fetch");
      return;
    }

    const fetchKeywords = async () => {
      setLoading(true);
      setError(null);

      const token = getToken();

      const params = new URLSearchParams({
        page: String(page),
        page_size: String(PAGE_SIZE),
      });
      if (search) params.set("search", search);

      // === DEBUG LOGS — remove after confirming working ===
      console.log("=== KEYWORDS FETCH DEBUG ===");
      console.log("Project ID:", projectId);
      console.log("Token:", token ? token.slice(0, 20) + "..." : "MISSING ⚠️");
      console.log("API Base:", API_BASE);
      // =====================================================

      // Try both URL patterns; whichever returns 200 wins
      const urls = [
        `${API_BASE}/api/v1/projects/${projectId}/keywords?${params}`,
        `${API_BASE}/api/v1/analysis/keywords/${projectId}?${params}`,
      ];

      let lastError = "";

      for (const url of urls) {
        try {
          console.log("[Keywords] Trying:", url);

          const response = await fetch(url, {
            headers: {
              "Content-Type": "application/json",
              Authorization: token ? `Bearer ${token}` : "",
            },
          });

          console.log("[Keywords] Status:", response.status);

          // Auto-logout on expired session
          if (response.status === 401) {
            console.warn("[Keywords] 401 — session expired, redirecting to /login");
            localStorage.removeItem("token");
            localStorage.removeItem("access_token");
            window.location.href = "/login";
            return;
          }

          if (response.ok) {
            const data = await response.json();
            console.log("[Keywords] Data keys:", Object.keys(data));

            const items: Keyword[] =
              data.keywords || data.items || data.data || data.results || [];
            const count: number =
              data.total ?? data.count ?? data.total_count ?? items.length;

            setKeywords(items);
            setTotal(count);
            setLoading(false);
            return; // success — stop trying
          }

          lastError = `HTTP ${response.status} from ${url}`;
          console.warn("[Keywords] Non-OK status:", response.status, "— trying next URL");
        } catch (err: any) {
          lastError = err.message;
          console.error("[Keywords] Fetch error:", err.message);
        }
      }

      // Both URLs failed
      setError(`Failed to load keywords: ${lastError}`);
      setLoading(false);
    };

    fetchKeywords();
  }, [projectId, page, search]);

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
        Select a project to view keywords.
      </div>
    );
  }

  const exportCSV = () => {
    const headers = ["Keyword", "Type", "Frequency"];
    const rows = keywords.map((kw) => [
      kw.keyword || "",
      kw.keyword_type || "KEYWORD",
      kw.frequency !== undefined ? kw.frequency : "",
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
    link.download = `keywords_project_${projectId}_${Date.now()}.csv`;
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
          Keywords
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
          disabled={keywords.length === 0}
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

      {/* Search */}
      <div style={{ position: "relative", marginBottom: "20px" }}>
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
          placeholder="Search keywords..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="form-input"
          style={{ width: "100%", paddingLeft: "2.25rem", boxSizing: "border-box" }}
        />
      </div>

      {/* States */}
      {loading && (
        <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
          Loading keywords...
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
            Failed to load keywords
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

      {!loading && !error && keywords.length === 0 && (
        <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
          <p style={{ fontSize: "16px", marginBottom: "8px" }}>No keywords found</p>
          <p style={{ fontSize: "13px" }}>
            Run an analysis to discover keywords for this project.
          </p>
        </div>
      )}

      {/* Table */}
      {!loading && keywords.length > 0 && (
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
                  Keyword
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
                    width: "140px",
                  }}
                >
                  Type
                </th>
                <th
                  style={{
                    padding: "12px 16px",
                    textAlign: "right",
                    fontWeight: 600,
                    color: "var(--text-muted)",
                    fontSize: "11px",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    width: "120px",
                  }}
                >
                  Frequency
                </th>
              </tr>
            </thead>
            <tbody>
              {keywords.map((kw, index) => (
                <tr
                  key={kw.id || index}
                  style={{
                    borderBottom: "1px solid var(--border)",
                    transition: "background var(--transition-fast)",
                  }}
                  className="table-row-hover"
                >
                  <td
                    style={{
                      padding: "14px 16px",
                      color: "var(--text-primary)",
                      fontWeight: 500,
                    }}
                  >
                    {kw.keyword}
                  </td>
                  <td style={{ padding: "14px 16px" }}>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        fontSize: "11px",
                        fontWeight: 600,
                        background:
                          kw.keyword_type === "PRIMARY"
                            ? "var(--primary-dim)"
                            : "var(--bg-card-hover)",
                        color:
                          kw.keyword_type === "PRIMARY"
                            ? "var(--primary)"
                            : "var(--text-muted)",
                        border: "1px solid transparent",
                      }}
                    >
                      {kw.keyword_type || "KEYWORD"}
                    </span>
                  </td>
                  <td
                    style={{
                      padding: "14px 16px",
                      textAlign: "right",
                      color: "var(--text-primary)",
                      fontFamily: "monospace",
                    }}
                  >
                    {kw.frequency || "-"}
                  </td>
                </tr>
              ))}
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
