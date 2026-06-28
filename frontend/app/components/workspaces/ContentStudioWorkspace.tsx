"use client";

import { useState } from "react";
import ContentOpportunitiesTab from "../ContentOpportunitiesTab";
import ContentIntelligenceTab from "../ContentIntelligenceTab";
import GenerateBlogsTab from "../GenerateBlogsTab";

interface ContentStudioWorkspaceProps {
  projectId: string;
  userId: string;
  results: any;
  blogs: any[];
  selectedBlogCount: number;
  generatingBlogs: boolean;
  onSelectCount: (count: number) => void;
  onGenerate: () => void;
}

export default function ContentStudioWorkspace({
  projectId,
  userId,
  results,
  blogs,
  selectedBlogCount,
  generatingBlogs,
  onSelectCount,
  onGenerate,
}: ContentStudioWorkspaceProps) {
  const [activeTab, setActiveTab] = useState<"opportunities" | "intelligence" | "blogs">("opportunities");

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
        <button style={tabStyle("opportunities")} onClick={() => setActiveTab("opportunities")}>
          Opportunities
        </button>
        <button style={tabStyle("intelligence")} onClick={() => setActiveTab("intelligence")}>
          Intelligence
        </button>
        <button style={tabStyle("blogs")} onClick={() => setActiveTab("blogs")}>
          Blog Generator
        </button>
      </div>

      {/* Tab Panel Render */}
      <div className="animate-fade-in">
        {activeTab === "opportunities" && (
          <ContentOpportunitiesTab
            contentOpportunities={results.content_opportunities || []}
            contentCoverage={results.content_coverage}
            gapAnalysis={results.gap_analysis}
          />
        )}
        {activeTab === "intelligence" && (
          <ContentIntelligenceTab projectId={projectId} userId={userId} />
        )}
        {activeTab === "blogs" && (
          <GenerateBlogsTab
            blogs={blogs}
            selectedBlogCount={selectedBlogCount}
            generatingBlogs={generatingBlogs}
            onSelectCount={onSelectCount}
            onGenerate={onGenerate}
          />
        )}
      </div>
    </div>
  );
}
