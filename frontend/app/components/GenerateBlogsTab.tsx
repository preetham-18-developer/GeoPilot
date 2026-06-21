"use client";

interface GenerateBlogsTabProps {
  blogs: any[];
  selectedBlogCount: number;
  generatingBlogs: boolean;
  onSelectCount: (count: number) => void;
  onGenerate: () => void;
}

export default function GenerateBlogsTab({
  blogs,
  selectedBlogCount,
  generatingBlogs,
  onSelectCount,
  onGenerate,
}: GenerateBlogsTabProps) {
  return (
    <div>
      <div className="card glow-border" style={{ marginBottom: "2.5rem" }}>
        <h2>Interactive Blog Generation Flow</h2>
        <p
          style={{
            color: "var(--text-muted)",
            margin: "0.5rem 0 2rem 0",
            fontSize: "0.95rem",
          }}
        >
          Select how many blogs you would like to generate based on verified
          factual assets, and trigger on-demand generation.
        </p>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "2rem",
            flexWrap: "wrap",
            marginBottom: "1.5rem",
          }}
        >
          <div style={{ display: "flex", gap: "1rem" }}>
            {[10, 50, 100].map((num) => (
              <label
                key={num}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  cursor: "pointer",
                  color: "var(--text-muted)",
                }}
              >
                <input
                  type="radio"
                  name="blogCount"
                  value={num}
                  checked={selectedBlogCount === num}
                  onChange={() => onSelectCount(num)}
                  style={{ accentColor: "var(--secondary)" }}
                />
                <span>Generate {num} Blogs</span>
              </label>
            ))}
          </div>

          <button
            className="btn btn-primary"
            onClick={onGenerate}
            disabled={generatingBlogs}
          >
            {generatingBlogs ? (
              <>
                <div className="spinner"></div>
                <span>Generating stubs...</span>
              </>
            ) : (
              <span>Generate Blogs</span>
            )}
          </button>
        </div>

        {generatingBlogs && (
          <p style={{ fontSize: "0.85rem", color: "var(--accent-amber)" }}>
            ⏳ Assembling factual references and drafting semantic headlines.
            This may take up to 10 seconds.
          </p>
        )}
      </div>

      <h2>Drafted Blog Publications ({blogs.length})</h2>
      <div className="grid-2">
        {blogs.length > 0 ? (
          blogs.map((blog: any, i: number) => (
            <div key={i} className="card glow-border" style={{ padding: "1.5rem" }}>
              <h3
                style={{
                  fontSize: "1.15rem",
                  marginBottom: "0.5rem",
                  color: "var(--secondary)",
                }}
              >
                {blog.title}
              </h3>

              <div
                style={{
                  fontSize: "0.85rem",
                  color: "var(--text-muted)",
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.5rem",
                }}
              >
                <div>
                  <strong>Target Keywords:</strong>{" "}
                  {blog.target_keywords?.map((kw: string, idx: number) => (
                    <span
                      key={idx}
                      className="badge badge-info"
                      style={{ marginRight: "0.25rem", fontSize: "0.75rem" }}
                    >
                      {kw}
                    </span>
                  ))}
                </div>
                <div>
                  <strong>Draft Summary:</strong> {blog.content}
                </div>
                <div
                  style={{
                    background: "rgba(255,255,255,0.01)",
                    borderLeft: "2px solid var(--border-color)",
                    paddingLeft: "1rem",
                    marginTop: "0.5rem",
                    fontStyle: "italic",
                    fontSize: "0.8rem",
                  }}
                >
                  <strong>Suggested Headers:</strong>
                  <br />
                  {blog.outline}
                </div>
              </div>
            </div>
          ))
        ) : (
          <div
            className="card flex-center"
            style={{ gridColumn: "1 / -1", padding: "4rem" }}
          >
            <p style={{ color: "var(--text-muted)" }}>
              No blogs generated yet. Select a count above and click
              &quot;Generate Blogs&quot;.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
