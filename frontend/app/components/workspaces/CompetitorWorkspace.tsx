"use client";

import { useState } from "react";
import CompetitorAnalysisTab from "../CompetitorAnalysisTab";
import CompetitorBenchmarkTab from "../CompetitorBenchmarkTab";

interface CompetitorWorkspaceProps {
  projectId: string;
  userId: string;
  results: any;
}

export default function CompetitorWorkspace({
  projectId,
  userId,
  results,
}: CompetitorWorkspaceProps) {
  const [activeTab, setActiveTab] = useState<"competitors" | "benchmark">("competitors");

  const tabStyle = (tab: typeof activeTab) => ({
    padding: "10px 16px",
    fontSize: "14px",
    fontWeight: 500,
    color: activeTab === tab ? "var(--primary)" : "var(--text-muted)",
    cursor: "pointer",
    background: "none",
    border: "none",
    borderBottom: activeTab === tab ? "2px solid var(--primary)" : "2px solid transparent",
    transition: "all var(--transition-fast)",
  });

  return (
    <div>
      {/* Internal Tabs Bar */}
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid var(--border)",
          marginBottom: "24px",
          gap: "8px",
        }}
      >
        <button style={tabStyle("competitors")} onClick={() => setActiveTab("competitors")}>
          Competitors
        </button>
        <button style={tabStyle("benchmark")} onClick={() => setActiveTab("benchmark")}>
          Benchmark Matrix
        </button>
      </div>

      {/* Tab Panel Render */}
      <div className="animate-fade-in">
        {activeTab === "competitors" && (
          <CompetitorAnalysisTab
            competitors={results.competitors || []}
            competitorFeatureMatrix={results.competitor_feature_matrix}
          />
        )}
        {activeTab === "benchmark" && (
          <CompetitorBenchmarkTab projectId={projectId} userId={userId} />
        )}
      </div>
    </div>
  );
}
