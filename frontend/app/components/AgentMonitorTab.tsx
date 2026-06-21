"use client";

interface AgentMonitorTabProps {
  agentRuns: any[];
  extractionFailures: any[];
}

export default function AgentMonitorTab({
  agentRuns,
  extractionFailures,
}: AgentMonitorTabProps) {
  return (
    <div>
      <h2>Agent Execution Monitor</h2>
      <p
        style={{
          color: "var(--text-muted)",
          fontSize: "0.9rem",
          marginBottom: "1.5rem",
        }}
      >
        Token consumption, latencies, and execution telemetry for all background
        agents.
      </p>
      <div className="table-container" style={{ marginBottom: "2.5rem" }}>
        <table className="custom-table">
          <thead>
            <tr>
              <th>Agent Name</th>
              <th>Execution Status</th>
              <th>Input Tokens</th>
              <th>Output Tokens</th>
              <th>Processing Time</th>
              <th>Error Message</th>
              <th>Executed At</th>
            </tr>
          </thead>
          <tbody>
            {agentRuns && agentRuns.length > 0 ? (
              agentRuns.map((run: any, i: number) => (
                <tr key={i}>
                  <td>
                    <strong>{run.agent_name}</strong>
                  </td>
                  <td>
                    <span
                      className={`badge ${
                        run.status === "completed" ? "badge-success" : "badge-danger"
                      }`}
                    >
                      {run.status}
                    </span>
                  </td>
                  <td>{run.input_tokens}</td>
                  <td>{run.output_tokens}</td>
                  <td>
                    {run.processing_time
                      ? `${run.processing_time.toFixed(2)}s`
                      : "-"}
                  </td>
                  <td style={{ color: "var(--accent-red)", fontSize: "0.85rem" }}>
                    {run.error_message || "-"}
                  </td>
                  <td style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                    {new Date(run.created_at).toLocaleString()}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td
                  colSpan={7}
                  style={{ textAlign: "center", color: "var(--text-dark)" }}
                >
                  No agent execution history recorded yet. Click &quot;Run AI
                  Crawler &amp; Agents&quot; to start.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Root Cause Analysis */}
      <h2>Root Cause Analysis Failure Log</h2>
      <p
        style={{
          color: "var(--text-muted)",
          fontSize: "0.9rem",
          marginBottom: "1.5rem",
        }}
      >
        Debugging dashboard for tracking page crawler timeouts, verified fact
        audits, and parser exceptions.
      </p>
      <div className="table-container">
        <table className="custom-table">
          <thead>
            <tr>
              <th>Failed URL</th>
              <th>Agent</th>
              <th>Reason for Failure</th>
              <th>Exception / Details</th>
              <th>Logged At</th>
            </tr>
          </thead>
          <tbody>
            {extractionFailures && extractionFailures.length > 0 ? (
              extractionFailures.map((f: any, i: number) => (
                <tr key={i}>
                  <td style={{ fontSize: "0.8rem" }}>
                    <a
                      href={f.page_url}
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: "var(--secondary)" }}
                    >
                      {f.page_url}
                    </a>
                  </td>
                  <td>
                    <span className="badge badge-info">{f.agent_name}</span>
                  </td>
                  <td style={{ color: "var(--accent-amber)", fontWeight: 600 }}>
                    {f.reason}
                  </td>
                  <td style={{ color: "var(--accent-red)", fontSize: "0.8rem" }}>
                    {f.error_message}
                  </td>
                  <td
                    style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}
                  >
                    {new Date(f.created_at).toLocaleString()}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td
                  colSpan={5}
                  style={{
                    textAlign: "center",
                    color: "var(--accent-green)",
                    fontWeight: 600,
                  }}
                >
                  ✓ No extraction or verification failures recorded. Clean
                  execution run!
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
