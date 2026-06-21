"use client";

interface ScoreBadgeProps {
  score: number;
  max?: number;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

function getScoreColor(score: number, max: number) {
  const pct = (score / max) * 100;
  if (pct >= 70) return "var(--accent-green)";
  if (pct >= 50) return "var(--accent-amber)";
  return "var(--accent-red)";
}

export default function ScoreBadge({
  score,
  max = 100,
  size = "md",
  showLabel = false,
}: ScoreBadgeProps) {
  const color = getScoreColor(score, max);
  const fontSize =
    size === "sm" ? "0.9rem" : size === "lg" ? "2.2rem" : "1.3rem";
  const fontWeight = size === "lg" ? 800 : 700;

  return (
    <span style={{ color, fontWeight, fontSize }}>
      {score}
      {showLabel && `/${max}`}
    </span>
  );
}
