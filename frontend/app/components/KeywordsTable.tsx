"use client";

import { useState, useEffect } from "react";
import { API_BASE, authHeader } from "../lib/config";

interface Keyword {
  id?: string;
  keyword: string;
  keyword_type: string;
  frequency: number;
}

interface KeywordsTableProps {
  projectId: string;
  userId: string;
}

export function KeywordsTable({ projectId, userId }: KeywordsTableProps) {
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectId) return;

    setLoading(true);
    fetch(
      `${API_BASE}/analysis/keywords/${projectId}` +
        `?page=${page}&page_size=50&search=${encodeURIComponent(search)}`,
      {
        headers: authHeader(userId),
      }
    )
      .then((r) => r.json())
      .then((data) => {
        setKeywords(data.keywords || []);
        setTotal(data.total || 0);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [projectId, userId, page, search]);

  const exportCSV = (kws: Keyword[]) => {
    const headers = ["Keyword", "Type", "Frequency"];
    const rows = kws.map((kw) => [
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
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `keywords_project_${projectId}_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="card animate-fade-in" style={{ padding: "24px", background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)" }}>
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
        <button className="btn btn-secondary btn-sm" onClick={() => exportCSV(keywords)} disabled={keywords.length === 0}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: "4px" }}>
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

      {/* Simple Table */}
      {loading ? (
        <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
          Loading keywords...
        </div>
      ) : keywords.length === 0 ? (
        <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
          No keywords found for this filter.
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
