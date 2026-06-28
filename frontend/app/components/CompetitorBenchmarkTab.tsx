"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE, authHeader } from "../lib/config";

interface GapItem {
  dimension: string;
  client_score: number;
  avg_competitor_score: number;
  best_competitor_score: number;
  gap_from_avg: number;
  gap_from_best: number;
  status: "strength" | "parity" | "weakness";
}

interface CompetitorScore {
  name: string;
  competitor_type: string;
  overall: number;
  scores: Record<string, number>;
}

interface BenchmarkReport {
  client_overall_score: number;
  percentile_score: number;
  relative_position: number;
  total_players: number;
  client_scores: Record<string, number>;
  competitor_scores: CompetitorScore[];
  gap_matrix: GapItem[];
  strengths_rank: GapItem[];
  weaknesses_rank: GapItem[];
  threats_rank: CompetitorScore[];
  opportunities_rank: GapItem[];
}

const ScoreRing = ({ score, size = 80 }: { score: number; size?: number }) => {
  const radius = (size - 12) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 70 ? "#10b981" : score >= 45 ? "#f59e0b" : "#ef4444";

  return (
    <svg width={size} height={size} className="rotate-[-90deg]">
      <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={8} />
      <circle
        cx={size / 2} cy={size / 2} r={radius}
        fill="none" stroke={color} strokeWidth={8}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        className="transition-all duration-700"
      />
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle"
        className="rotate-[90deg]" fill="white" fontSize={size < 60 ? "10" : "14"} fontWeight="700"
        transform={`rotate(90, ${size / 2}, ${size / 2})`}
      >
        {Math.round(score)}
      </text>
    </svg>
  );
};

const DimensionBar = ({ item }: { item: GapItem }) => {
  const clientPct = item.client_score;
  const avgPct = item.avg_competitor_score;
  const bestPct = item.best_competitor_score;
  const gap = item.gap_from_avg;

  const statusStyle = {
    strength: { color: "text-emerald-400", bg: "from-emerald-500 to-teal-400", badge: "bg-emerald-500/20 border-emerald-500/30 text-emerald-400" },
    parity: { color: "text-amber-400", bg: "from-amber-500 to-yellow-400", badge: "bg-amber-500/20 border-amber-500/30 text-amber-400" },
    weakness: { color: "text-red-400", bg: "from-red-500 to-orange-400", badge: "bg-red-500/20 border-red-500/30 text-red-400" },
  }[item.status];

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-4 hover:border-white/20 transition-all">
      <div className="flex items-center justify-between mb-3">
        <span className="text-white text-sm font-semibold">{item.dimension}</span>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-bold ${gap >= 0 ? "text-emerald-400" : "text-red-400"}`}>
            {gap >= 0 ? "+" : ""}{gap.toFixed(1)}
          </span>
          <span className={`text-xs px-2 py-0.5 rounded-full border font-semibold ${statusStyle.badge}`}>
            {item.status}
          </span>
        </div>
      </div>

      {/* Client bar */}
      <div className="space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="text-xs text-white/40 w-12">Client</span>
          <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
            <div className={`h-full rounded-full bg-gradient-to-r ${statusStyle.bg} transition-all duration-700`} style={{ width: `${clientPct}%` }} />
          </div>
          <span className="text-xs text-white/60 w-8 text-right">{clientPct.toFixed(0)}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-white/40 w-12">Avg</span>
          <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
            <div className="h-full rounded-full bg-white/20 transition-all duration-700" style={{ width: `${avgPct}%` }} />
          </div>
          <span className="text-xs text-white/60 w-8 text-right">{avgPct.toFixed(0)}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-white/40 w-12">Best</span>
          <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
            <div className="h-full rounded-full bg-violet-400/40 transition-all duration-700" style={{ width: `${bestPct}%` }} />
          </div>
          <span className="text-xs text-white/60 w-8 text-right">{bestPct.toFixed(0)}</span>
        </div>
      </div>
    </div>
  );
};

export default function CompetitorBenchmarkTab({ projectId, userId }: { projectId: string; userId: string }) {
  const [report, setReport] = useState<BenchmarkReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<"matrix" | "competitors">("matrix");

  const fetchBenchmark = useCallback(async (showRefresh = false) => {
    if (!projectId) return;
    if (showRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/analysis/competitor-benchmark/${projectId}`, { headers: authHeader(userId) });
      if (!res.ok) throw new Error(await res.text());
      setReport(await res.json());
    } catch (e: unknown) {
      setError("Failed to load benchmark report.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [projectId, userId]);

  useEffect(() => { fetchBenchmark(); }, [fetchBenchmark]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-white/50 text-sm">Running benchmark analysis…</span>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <div className="text-red-400 text-sm">{error || "No data available."}</div>
        <button onClick={() => fetchBenchmark()} className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-xl text-sm font-semibold transition-all">
          Retry
        </button>
      </div>
    );
  }

  const dimensions = Object.keys(report.client_scores).map((k) => k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Competitor Benchmark</h2>
          <p className="text-white/50 text-sm mt-0.5">7-dimension gap analysis vs all stored competitors</p>
        </div>
        <button
          onClick={() => fetchBenchmark(true)}
          disabled={refreshing}
          className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 disabled:opacity-50 text-white text-sm font-semibold transition-all flex items-center gap-2"
        >
          {refreshing ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>}
          Refresh
        </button>
      </div>

      {/* Score Banner */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-gradient-to-br from-violet-600/30 to-indigo-600/20 border border-violet-500/30 rounded-2xl p-5 flex flex-col items-center">
          <ScoreRing score={report.client_overall_score} size={80} />
          <div className="text-white/60 text-sm mt-2">Overall Score</div>
        </div>
        <div className="bg-white/5 border border-white/10 rounded-2xl p-5 flex flex-col items-center justify-center">
          <div className="text-3xl font-bold text-white">{report.percentile_score}%</div>
          <div className="text-white/60 text-sm mt-1">Percentile</div>
          <div className="text-white/30 text-xs mt-0.5">Beats this % of competitors</div>
        </div>
        <div className="bg-white/5 border border-white/10 rounded-2xl p-5 flex flex-col items-center justify-center">
          <div className="text-3xl font-bold text-white">#{report.relative_position}</div>
          <div className="text-white/60 text-sm mt-1">Rank</div>
          <div className="text-white/30 text-xs mt-0.5">of {report.total_players} players</div>
        </div>
        <div className="bg-white/5 border border-white/10 rounded-2xl p-5 flex flex-col items-center justify-center">
          <div className="text-3xl font-bold text-emerald-400">{report.strengths_rank.length}</div>
          <div className="text-white/60 text-sm mt-1">Strengths</div>
          <div className="text-red-400 text-xs mt-0.5">{report.weaknesses_rank.length} weaknesses</div>
        </div>
      </div>

      {/* View Toggle */}
      <div className="flex gap-2 p-1 bg-white/5 rounded-xl w-fit border border-white/10">
        {(["matrix", "competitors"] as const).map((v) => (
          <button
            key={v}
            onClick={() => setActiveView(v)}
            className={`px-4 py-1.5 rounded-lg text-sm font-semibold transition-all capitalize ${
              activeView === v ? "bg-violet-600 text-white" : "text-white/50 hover:text-white"
            }`}
          >
            {v === "matrix" ? "Gap Matrix" : "Competitor Scores"}
          </button>
        ))}
      </div>

      {activeView === "matrix" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {report.gap_matrix.map((item) => (
            <DimensionBar key={item.dimension} item={item} />
          ))}
        </div>
      )}

      {activeView === "competitors" && (
        <div className="space-y-3">
          {report.competitor_scores.length === 0 ? (
            <div className="text-center py-12 text-white/30">No competitor data available. Run an analysis first.</div>
          ) : (
            report.competitor_scores.map((comp, idx) => (
              <div key={idx} className="bg-white/5 border border-white/10 rounded-2xl p-4 flex items-center gap-4">
                <ScoreRing score={comp.overall} size={52} />
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-white font-semibold text-sm">{comp.name}</span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-white/10 text-white/50 capitalize">{comp.competitor_type}</span>
                  </div>
                  <div className="grid grid-cols-3 md:grid-cols-7 gap-2">
                    {Object.entries(comp.scores).map(([dim, val]) => (
                      <div key={dim} className="text-center">
                        <div className="text-xs text-white/40 mb-0.5">{dim.split("_")[0]}</div>
                        <div className={`text-xs font-bold ${val >= 70 ? "text-emerald-400" : val >= 45 ? "text-amber-400" : "text-red-400"}`}>{val}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Opportunities Panel */}
      {report.opportunities_rank.length > 0 && (
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-5">
          <h3 className="text-amber-400 font-semibold text-sm mb-3 flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
            Top Improvement Opportunities
          </h3>
          <div className="space-y-2">
            {report.opportunities_rank.slice(0, 3).map((opp) => (
              <div key={opp.dimension} className="flex items-center justify-between">
                <span className="text-white/70 text-sm">{opp.dimension}</span>
                <span className="text-red-400 text-xs font-bold">{opp.gap_from_avg.toFixed(1)} behind avg</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
