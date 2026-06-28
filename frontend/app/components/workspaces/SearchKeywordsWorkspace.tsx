"use client";

import { useState } from "react";
import { QuestionsTable } from "../QuestionsTable";
import { KeywordsTable } from "../KeywordsTable";
import ValidationTab from "../ValidationTab";

interface SearchKeywordsWorkspaceProps {
  projectId: string;
  userId: string;
  results: any;
  qHook: any;
  kHook: any;
}

export default function SearchKeywordsWorkspace({
  projectId,
  userId,
  results,
  qHook,
  kHook,
}: SearchKeywordsWorkspaceProps) {
  const [activeTab, setActiveTab] = useState<"questions" | "keywords" | "validation">("questions");

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
        <button style={tabStyle("questions")} onClick={() => setActiveTab("questions")}>
          Questions
        </button>
        <button style={tabStyle("keywords")} onClick={() => setActiveTab("keywords")}>
          Keyword Clusters
        </button>
        <button style={tabStyle("validation")} onClick={() => setActiveTab("validation")}>
          Validation
        </button>
      </div>

      {/* Tab Panel Render */}
      <div className="animate-fade-in">
        {activeTab === "questions" && (
          <QuestionsTable projectId={projectId} userId={userId} />
        )}
        {activeTab === "keywords" && (
          <KeywordsTable projectId={projectId} userId={userId} />
        )}
        {activeTab === "validation" && (
          <ValidationTab projectId={projectId} userId={userId} />
        )}
      </div>
    </div>
  );
}
