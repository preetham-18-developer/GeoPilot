"use client";

interface ReportsTabProps {
  latestReport: any;
  selectedProjectId: string | null;
  onDownload: (format: string) => void;
}

export default function ReportsTab({
  latestReport,
  selectedProjectId,
  onDownload,
}: ReportsTabProps) {
  return (
    <div className="card">
      <h2>Export Optimization Reports</h2>
      <p style={{ color: "var(--text-muted)", margin: "0.5rem 0 2rem 0" }}>
        Download your AI Visibility optimization package in Markdown format
        (perfect for reading or copying straight to documentation) or JSON
        format (for third-party system integrations).
      </p>

      {latestReport ? (
        <div style={{ display: "flex", gap: "1.5rem" }}>
          <button
            className="btn btn-primary"
            onClick={() => onDownload("markdown")}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              style={{ marginRight: "0.25rem" }}
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v4M7 10l5 5 5-5M12 15V3" />
            </svg>
            Download Markdown (.md)
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => onDownload("json")}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              style={{ marginRight: "0.25rem" }}
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v4M7 10l5 5 5-5M12 15V3" />
            </svg>
            Download JSON (.json)
          </button>
        </div>
      ) : (
        <p style={{ color: "var(--accent-red)" }}>
          No report available yet. Please execute an analysis run first.
        </p>
      )}
    </div>
  );
}
