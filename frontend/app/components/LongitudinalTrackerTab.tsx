"use client";

import { useState, useEffect, useCallback } from "react";

interface ScorePoint {
  created_at: string;
  visibility_score: number;
  recommendation_score: number;
  hallucination_score: number;
  consistency_score: number;
  coverage_score: number;
}

interface TrendEntry {
  current: number;
  weekly_delta: number;
  weekly_direction: string;
  monthly_delta: number;
  monthly_direction: string;
  velocity: number;
  velocity_direction: string;
}

interface RegressionWarning {
  metric: string;
  previous: number;
  current: number;
  drop: number;
  severity: "warning" | "critical";
}

interface ImprovementFlag {
  metric: string;
  start: number;
  current: number;
  gain: number;
}

interface HistoricalData {
  total_runs: number;
  runs: ScorePoint[];
  trends: Record<string, TrendEntry>;
  regression_warnings: RegressionWarning[];
  improvement_flags: ImprovementFlag[];
}

const METRICS = [
  { key: "visibility_score", label: "Visibility", color: "#8b5cf6" },
  { key: "recommendation_score", label: "Recommendation", color: "#06b6d4" },
  { key: "hallucination_score", label: "Hallucination Safety", color: "#10b981" },
  { key: "consistency_score", label: "Consistency", color: "#f59e0b" },
  { key: "coverage_score", label: "Coverage", color: "#ec4899" },
];

const DirectionIcon = ({ direction }: { direction: string }) => {
  if (direction === "improving") return <span className="text-emerald-400">▲</span>;
  if (direction === "declining") return <span className="text-red-400">▼</span>;
  return <span className="text-white/40">→</span>;
};

const MiniSparkline = ({ runs, metricKey, color }: { runs: ScorePoint[]; metricKey: string; color: string }) => {
  if (runs.length < 2) return <div className="h-8 text-white/20 text-xs flex items-center">Not enough data</div>;

  const vals = runs.map((r) => (r as unknown as Record<string, number>)[metricKey] ?? 0);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const W = 120;
  const H = 32;

  const points = vals
    .map((v, i) => {
      const x = (i / (vals.length - 1)) * W;
      const y = H - ((v - min) / range) * H;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
      <polyline points={points} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
      {vals.map((v, i) => {
        const x = (i / (vals.length - 1)) * W;
        const y = H - ((v - min) / range) * H;
        return <circle key={i} cx={x} cy={y} r={2} fill={color} />;
      })}
    </svg>
  );
};

export default function LongitudinalTrackerTab({ projectId }: { projectId: string }) {
  const [data, setData] = useState<HistoricalData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeMetric, setActiveMetric] = useState<string>("visibility_score");

  const fetchHistory = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/analysis/historical-metrics/${projectId}`, { credentials: "include" });
      if (!res.ok) throw new Error(await res.text());
      setData(await res.json());
    } catch {
      setError("Failed to load historical metrics.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { fetchHistory(); }, [fetchHistory]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-white/50 text-sm">Loading historical data…</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <div className="text-red-400 text-sm">{error}</div>
        <button onClick={fetchHistory} className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl text-sm font-semibold transition-all">Retry</button>
      </div>
    );
  }

  const noData = !data || data.total_runs === 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Longitudinal Tracker</h2>
          <p className="text-white/50 text-sm mt-0.5">Score trends, velocity, and regression monitoring across runs</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded-xl">
          <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <span className="text-white/60 text-sm">{data?.total_runs || 0} runs tracked</span>
        </div>
      </div>

      {/* Regression Warnings */}
      {data?.regression_warnings && data.regression_warnings.length > 0 && (
        <div className="space-y-2">
          {data.regression_warnings.map((w, i) => (
            <div key={i} className={`flex items-center justify-between p-4 rounded-xl border ${
              w.severity === "critical" ? "bg-red-500/10 border-red-500/30" : "bg-amber-500/10 border-amber-500/30"
            }`}>
              <div className="flex items-center gap-3">
                <span className={`text-lg ${w.severity === "critical" ? "text-red-400" : "text-amber-400"}`}>
                  {w.severity === "critical" ? "⚠️" : "⚡"}
                </span>
                <div>
                  <div className={`font-semibold text-sm ${w.severity === "critical" ? "text-red-400" : "text-amber-400"}`}>
                    {w.metric} Regression
                  </div>
                  <div className="text-white/50 text-xs">{w.previous} → {w.current} (−{w.drop} pts)</div>
                </div>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full border font-semibold ${
                w.severity === "critical" ? "bg-red-500/20 border-red-500/30 text-red-400" : "bg-amber-500/20 border-amber-500/30 text-amber-400"
              }`}>
                {w.severity.toUpperCase()}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Improvement Flags */}
      {data?.improvement_flags && data.improvement_flags.length > 0 && (
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-2xl p-4">
          <div className="text-emerald-400 font-semibold text-sm mb-3 flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Improvement Milestones
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {data.improvement_flags.map((f, i) => (
              <div key={i} className="bg-emerald-500/10 rounded-xl p-3">
                <div className="text-white/70 text-xs font-medium">{f.metric}</div>
                <div className="text-emerald-400 font-bold text-lg">+{f.gain} pts</div>
                <div className="text-white/30 text-xs">{f.start} → {f.current}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {noData ? (
        <div className="text-center py-16 text-white/30">
          <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          No historical data yet. Run multiple analyses to see trends.
        </div>
      ) : (
        <>
          {/* Metric Selector + Sparklines */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {METRICS.map((m) => {
              const trend = data?.trends?.[m.key];
              const isActive = activeMetric === m.key;
              return (
                <button
                  key={m.key}
                  onClick={() => setActiveMetric(m.key)}
                  className={`bg-white/5 border rounded-2xl p-4 text-left transition-all ${
                    isActive ? "border-violet-500/50 bg-violet-500/10" : "border-white/10 hover:border-white/20"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-white/60 text-xs font-medium">{m.label}</span>
                    {trend && <DirectionIcon direction={trend.weekly_direction} />}
                  </div>
                  <div className="text-xl font-bold text-white mb-2">{trend?.current?.toFixed(0) ?? "—"}</div>
                  <MiniSparkline runs={data?.runs || []} metricKey={m.key} color={m.color} />
                </button>
              );
            })}
          </div>

          {/* Selected Metric Detail */}
          {data?.trends?.[activeMetric] && (() => {
            const t = data.trends[activeMetric];
            const m = METRICS.find((x) => x.key === activeMetric)!;
            return (
              <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: m.color }} />
                  <h3 className="text-white font-semibold">{m.label} — Detailed Trend</h3>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  {[
                    { label: "Weekly Δ", value: t.weekly_delta, dir: t.weekly_direction },
                    { label: "Monthly Δ", value: t.monthly_delta, dir: t.monthly_direction },
                    { label: "Velocity", value: t.velocity, dir: t.velocity_direction },
                  ].map((stat) => (
                    <div key={stat.label} className="bg-white/5 rounded-xl p-3">
                      <div className="text-white/40 text-xs mb-1">{stat.label}</div>
                      <div className={`text-lg font-bold flex items-center gap-1 ${
                        stat.value > 0 ? "text-emerald-400" : stat.value < 0 ? "text-red-400" : "text-white/60"
                      }`}>
                        {stat.value >= 0 ? "+" : ""}{stat.value.toFixed(1)}
                        <DirectionIcon direction={stat.dir} />
                      </div>
                      <div className="text-white/30 text-xs capitalize">{stat.dir}</div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}

          {/* Run History Table */}
          {data.runs.length > 0 && (
            <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
              <div className="px-5 py-3 border-b border-white/10">
                <h3 className="text-white font-semibold text-sm">All Runs</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-white/5">
                      <th className="px-5 py-3 text-left text-white/40 font-medium">Date</th>
                      {METRICS.map((m) => (
                        <th key={m.key} className="px-3 py-3 text-center text-white/40 font-medium">{m.label}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.runs.slice().reverse().map((run, idx) => (
                      <tr key={idx} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                        <td className="px-5 py-3 text-white/60">
                          {new Date(run.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "2-digit" })}
                        </td>
                        {METRICS.map((m) => {
                          const val = (run as unknown as Record<string, number>)[m.key] ?? 0;
                          return (
                            <td key={m.key} className="px-3 py-3 text-center">
                              <span className={`font-bold ${val >= 70 ? "text-emerald-400" : val >= 45 ? "text-amber-400" : "text-red-400"}`}>
                                {val.toFixed(0)}
                              </span>
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
