"use client";

import { useState } from "react";
import OptimizationIntelligenceTab from "../OptimizationIntelligenceTab";
import AutonomousExecutionTab from "../AutonomousExecutionTab";
import ReliabilityDashboard from "../ReliabilityDashboard";
import AgentMonitorTab from "../AgentMonitorTab";
import { ChevronDown } from "../ui/Icons";

interface SystemHealthWorkspaceProps {
  projectId: string;
  userId: string;
  results: any;
}

function CollapsibleAccordion({ title, children }: { title: string; children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: "8px", overflow: "hidden", background: "var(--bg-card)" }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          width: "100%",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "16px 20px",
          fontFamily: "var(--font-title)",
          fontSize: "15px",
          fontWeight: 600,
          background: "none",
          border: "none",
          cursor: "pointer",
          color: "var(--text-primary)",
          textAlign: "left",
        }}
      >
        <span>{title}</span>
        <ChevronDown
          style={{
            transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform var(--transition-fast)",
            opacity: 0.7,
          }}
        />
      </button>
      {isOpen && (
        <div style={{ padding: "20px", borderTop: "1px solid var(--border)", background: "var(--bg-base)" }}>
          {children}
        </div>
      )}
    </div>
  );
}

export default function SystemHealthWorkspace({
  projectId,
  userId,
  results,
}: SystemHealthWorkspaceProps) {
  const [activeTab, setActiveTab] = useState<"strategy" | "logs" | "reliability">("strategy");

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
        <button style={tabStyle("strategy")} onClick={() => setActiveTab("strategy")}>
          Strategy Roadmap
        </button>
        <button style={tabStyle("logs")} onClick={() => setActiveTab("logs")}>
          Agent Logs
        </button>
        <button style={tabStyle("reliability")} onClick={() => setActiveTab("reliability")}>
          Reliability
        </button>
      </div>

      {/* Tab Panel Render */}
      <div className="animate-fade-in">
        {activeTab === "strategy" && (
          <OptimizationIntelligenceTab projectId={projectId} userId={userId} />
        )}
        {activeTab === "logs" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            <AutonomousExecutionTab projectId={projectId} userId={userId} />
            
            {/* Agent Monitor inline accordion below the logs */}
            <CollapsibleAccordion title="Agent Monitor & Health Status">
              <AgentMonitorTab
                agentRuns={results.agent_runs || []}
                extractionFailures={results.extraction_failures || []}
              />
            </CollapsibleAccordion>
          </div>
        )}
        {activeTab === "reliability" && (
          <ReliabilityDashboard projectId={projectId} userId={userId} />
        )}
      </div>
    </div>
  );
}
