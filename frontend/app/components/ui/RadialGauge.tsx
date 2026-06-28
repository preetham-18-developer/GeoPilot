"use client";

import React from "react";

/**
 * Reusable Radial Gauge (SVG-based).
 * Used in OverviewTab, ReliabilityDashboard, OptimizationIntelligenceTab.
 * Replaces 4 copy-pasted SVG circle patterns.
 */
interface RadialGaugeProps {
  value: number;         // 0–100
  size?: number;         // diameter in px
  strokeWidth?: number;
  color?: string;
  trackColor?: string;
  label?: React.ReactNode;
  sublabel?: string;
  animate?: boolean;
}

export function RadialGauge({
  value,
  size = 120,
  strokeWidth = 3.5,
  color = "var(--primary)",
  trackColor = "rgba(255,255,255,0.06)",
  label,
  sublabel,
  animate = true,
}: RadialGaugeProps) {
  const clamped = Math.max(0, Math.min(100, value));

  return (
    <div
      className="radial-gauge-wrap"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Score: ${clamped}%`}
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 40 40"
        style={{ display: "block" }}
      >
        {/* Track */}
        <path
          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          fill="none"
          stroke={trackColor}
          strokeWidth={strokeWidth}
        />
        {/* Fill */}
        <path
          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${clamped}, 100`}
          style={animate ? { transition: "stroke-dasharray 0.8s cubic-bezier(0.4, 0, 0.2, 1)" } : {}}
        />
      </svg>
      <div className="radial-gauge-label">
        {label ?? (
          <span style={{ fontSize: size > 100 ? "1.5rem" : "1rem", fontWeight: 700, color: "#fff" }}>
            {clamped}
          </span>
        )}
        {sublabel && (
          <div style={{ fontSize: "0.6rem", color: "var(--text-muted)", marginTop: 2, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            {sublabel}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Score color helper — consistent across all components.
 */
export function getScoreColor(score: number): string {
  if (score >= 80) return "var(--accent-green)";
  if (score >= 60) return "var(--accent-amber)";
  if (score >= 40) return "var(--secondary)";
  return "var(--accent-red)";
}

export function getScoreLabel(score: number): string {
  if (score >= 80) return "Excellent";
  if (score >= 60) return "Good";
  if (score >= 40) return "Fair";
  return "Poor";
}

export function getScoreBadgeClass(score: number): string {
  if (score >= 80) return "badge-success";
  if (score >= 60) return "badge-warning";
  return "badge-danger";
}

/**
 * Linear progress bar.
 */
interface ProgressBarProps {
  value: number;
  color?: string;
  height?: number;
  showLabel?: boolean;
  label?: string;
}

export function ProgressBar({ value, color, height = 6, showLabel = false, label }: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, value));
  const barColor = color ?? getScoreColor(clamped);

  return (
    <div>
      {(showLabel || label) && (
        <div className="flex justify-between mb-1">
          {label && <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{label}</span>}
          {showLabel && <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{clamped}%</span>}
        </div>
      )}
      <div className="progress-bar-track" style={{ height }}>
        <div
          className="progress-bar-fill"
          style={{ width: `${clamped}%`, background: barColor, transition: "width 0.6s ease-in-out" }}
        />
      </div>
    </div>
  );
}

/**
 * Stat card for key metrics — used in executive dashboard.
 */
interface StatCardProps {
  label: string;
  value: string | number;
  delta?: string;
  deltaPositive?: boolean;
  icon?: React.ReactNode;
  accent?: string;
  score?: number; // If provided, renders a mini progress bar
}

export function StatCard({ label, value, delta, deltaPositive, icon, accent, score }: StatCardProps) {
  return (
    <div className="stat-card">
      <div className="flex justify-between items-start">
        <span className="stat-label">{label}</span>
        {icon && <div style={{ color: accent ?? "var(--primary)", opacity: 0.8 }}>{icon}</div>}
      </div>
      <div className="stat-value" style={accent ? { color: accent } : {}}>
        {value}
      </div>
      {score !== undefined && (
        <ProgressBar value={score} color={accent} height={4} />
      )}
      {delta && (
        <span className={`stat-delta ${deltaPositive ? "positive" : "negative"}`}>
          {deltaPositive ? "↑" : "↓"} {delta}
        </span>
      )}
    </div>
  );
}
