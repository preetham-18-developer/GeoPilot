"use client";

import { useState } from "react";
import RecommendationIntelligenceTab from "../RecommendationIntelligenceTab";
import RealityCheckerTab from "../RealityCheckerTab";
import GEOIntelligenceTab from "../GEOIntelligenceTab";
import AdvancedAnalyticsTab from "../AdvancedAnalyticsTab";
import LongitudinalTrackerTab from "../LongitudinalTrackerTab";
import { ChevronDown } from "../ui/Icons";

interface SimulationWorkspaceProps {
  projectId: string;
  userId: string;
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

export default function SimulationWorkspace({
  projectId,
  userId,
}: SimulationWorkspaceProps) {
  const [activeTab, setActiveTab] = useState<"probabilities" | "reality" | "geo">("probabilities");

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
        <button style={tabStyle("probabilities")} onClick={() => setActiveTab("probabilities")}>
          LLM Probabilities
        </button>
        <button style={tabStyle("reality")} onClick={() => setActiveTab("reality")}>
          Reality Checker
        </button>
        <button style={tabStyle("geo")} onClick={() => setActiveTab("geo")}>
          GEO Scoring
        </button>
      </div>

      {/* Tab Panel Render */}
      <div className="animate-fade-in">
        {activeTab === "probabilities" && (
          <RecommendationIntelligenceTab projectId={projectId} userId={userId} />
        )}
        {activeTab === "reality" && (
          <RealityCheckerTab projectId={projectId} userId={userId} />
        )}
        {activeTab === "geo" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            <GEOIntelligenceTab projectId={projectId} userId={userId} />
            
            {/* Accordion for Analytics & Tracker at the bottom */}
            <CollapsibleAccordion title="Advanced Analytics & Historical Tracker">
              <div style={{ display: "flex", flexDirection: "column", gap: "32px" }}>
                <div>
                  <h3 style={{ marginBottom: "16px", fontSize: "16px", fontFamily: "var(--font-title)" }}>
                    Advanced Analytics Breakdown
                  </h3>
                  <AdvancedAnalyticsTab projectId={projectId} userId={userId} />
                </div>
                <div style={{ borderTop: "1px solid var(--border)", paddingTop: "24px" }}>
                  <h3 style={{ marginBottom: "16px", fontSize: "16px", fontFamily: "var(--font-title)" }}>
                    Longitudinal Tracker Index
                  </h3>
                  <LongitudinalTrackerTab projectId={projectId} userId={userId} />
                </div>
              </div>
            </CollapsibleAccordion>
          </div>
        )}
      </div>
    </div>
  );
}
