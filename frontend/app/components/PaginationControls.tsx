"use client";

interface PaginationControlsProps {
  page: number;
  totalCount: number;
  pageSize?: number;
  loading?: boolean;
  onPrev: () => void;
  onNext: () => void;
  label?: string;
}

export default function PaginationControls({
  page,
  totalCount,
  pageSize = 10,
  loading = false,
  onPrev,
  onNext,
  label = "items",
}: PaginationControlsProps) {
  const totalPages = Math.ceil(totalCount / pageSize) || 1;
  const startItem = (page - 1) * pageSize + 1;
  const endItem = Math.min(page * pageSize, totalCount);

  if (totalCount === 0) return null;

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginTop: "1.5rem",
        flexWrap: "wrap",
        gap: "1rem",
      }}
    >
      <div style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>
        Showing {startItem} to {endItem} of {totalCount} {label}
      </div>
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button
          className="btn btn-secondary"
          disabled={page === 1 || loading}
          onClick={onPrev}
          style={{ padding: "0.4rem 0.8rem", fontSize: "0.85rem" }}
        >
          Previous
        </button>
        <span
          style={{
            display: "flex",
            alignItems: "center",
            padding: "0 0.5rem",
            fontSize: "0.9rem",
          }}
        >
          Page {page} of {totalPages}
        </span>
        <button
          className="btn btn-secondary"
          disabled={page >= totalPages || loading}
          onClick={onNext}
          style={{ padding: "0.4rem 0.8rem", fontSize: "0.85rem" }}
        >
          Next
        </button>
      </div>
    </div>
  );
}
