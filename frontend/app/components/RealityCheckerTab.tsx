"use client";

import { useState, useEffect, useCallback } from "react";

interface RealityCheck {
  id: string;
  query: string;
  expected_confidence: number;
  evidence: string[];
  chatgpt_mentions: string;
  gemini_mentions: string;
  perplexity_mentions: string;
  is_verified: boolean;
}

interface RealityMetrics {
  accuracy: number;
  precision: number;
  recall: number;
  calibration_error: number;
  total_checks: number;
  verified_checks: number;
}

const MentionBadge = ({ value }: { value: string }) => {
  const styles: Record<string, string> = {
    YES: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30",
    NO: "bg-red-500/20 text-red-400 border border-red-500/30",
    PARTIAL: "bg-amber-500/20 text-amber-400 border border-amber-500/30",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${styles[value?.toUpperCase()] || "bg-white/10 text-white/60 border border-white/10"}`}>
      {value || "—"}
    </span>
  );
};

const ConfidenceBar = ({ value }: { value: number }) => {
  const pct = Math.round(value * 100);
  const color = pct >= 70 ? "from-emerald-500 to-teal-400" : pct >= 40 ? "from-amber-500 to-yellow-400" : "from-red-500 to-orange-400";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
        <div className={`h-full rounded-full bg-gradient-to-r ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-white/60 w-8 text-right">{pct}%</span>
    </div>
  );
};

export default function RealityCheckerTab({ projectId }: { projectId: string }) {
  const [checks, setChecks] = useState<RealityCheck[]>([]);
  const [metrics, setMetrics] = useState<RealityMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [verifyingId, setVerifyingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [verifyState, setVerifyState] = useState<Record<string, { chatgpt: string; gemini: string; perplexity: string }>>({});

  const fetchAll = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const [checksRes, metricsRes] = await Promise.all([
        fetch(`/api/analysis/reality-check/${projectId}`, { credentials: "include" }),
        fetch(`/api/analysis/reality-check/metrics/${projectId}`, { credentials: "include" }),
      ]);
      const checksData = await checksRes.json();
      const metricsData = await metricsRes.json();
      setChecks(checksData.reality_checks || []);
      setMetrics(metricsData);
    } catch (e: unknown) {
      setError("Failed to load reality checks. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const res = await fetch(`/api/analysis/reality-check/${projectId}/generate`, {
        method: "POST",
        credentials: "include",
      });
      const data = await res.json();
      setChecks(data.reality_checks || []);
      await fetchMetrics();
    } catch {
      setError("Failed to generate queries.");
    } finally {
      setGenerating(false);
    }
  };

  const fetchMetrics = async () => {
    try {
      const res = await fetch(`/api/analysis/reality-check/metrics/${projectId}`, { credentials: "include" });
      setMetrics(await res.json());
    } catch {}
  };

  const handleVerify = async (checkId: string) => {
    const state = verifyState[checkId];
    if (!state) return;
    setVerifyingId(checkId);
    try {
      await fetch(`/api/analysis/reality-check/${projectId}/verify/${checkId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          chatgpt_mentions: state.chatgpt || "NO",
          gemini_mentions: state.gemini || "NO",
          perplexity_mentions: state.perplexity || "NO",
        }),
      });
      setChecks((prev) =>
        prev.map((c) =>
          c.id === checkId
            ? { ...c, is_verified: true, chatgpt_mentions: state.chatgpt || "NO", gemini_mentions: state.gemini || "NO", perplexity_mentions: state.perplexity || "NO" }
            : c
        )
      );
      await fetchMetrics();
    } catch {
      setError("Failed to save verification.");
    } finally {
      setVerifyingId(null);
    }
  };

  const MENTION_OPTIONS = ["YES", "NO", "PARTIAL"];

  const metricCards = metrics
    ? [
        { label: "Accuracy", value: metrics.accuracy, desc: "Correct yes/no predictions" },
        { label: "Precision", value: metrics.precision, desc: "True positives / predicted positives" },
        { label: "Recall", value: metrics.recall, desc: "True positives / actual positives" },
        { label: "Calibration Error", value: 1 - metrics.calibration_error, desc: "Lower error = better" },
      ]
    : [];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-white/50 text-sm">Loading reality checks…</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Reality Checker</h2>
          <p className="text-white/50 text-sm mt-0.5">
            Test whether AI models actually recommend this business.
          </p>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-sm font-semibold transition-all flex items-center gap-2"
        >
          {generating ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Generating…
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Regenerate Queries
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>
      )}

      {/* Metrics Strip */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {metricCards.map((m) => (
            <div key={m.label} className="bg-white/5 border border-white/10 rounded-2xl p-4">
              <div className="text-2xl font-bold text-white">{Math.round(m.value * 100)}%</div>
              <div className="text-sm font-semibold text-white/80 mt-0.5">{m.label}</div>
              <div className="text-xs text-white/40 mt-1">{m.desc}</div>
            </div>
          ))}
        </div>
      )}

      {/* Progress Chip */}
      {metrics && (
        <div className="flex items-center gap-3 p-3 bg-white/5 border border-white/10 rounded-xl">
          <div className="w-2 h-2 rounded-full bg-emerald-400" />
          <span className="text-white/60 text-sm">
            <span className="text-white font-semibold">{metrics.verified_checks}</span> of{" "}
            <span className="text-white font-semibold">{metrics.total_checks}</span> queries manually verified
          </span>
        </div>
      )}

      {/* Query Table */}
      {checks.length === 0 ? (
        <div className="text-center py-16 text-white/30">
          <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          No reality checks generated yet. Click &quot;Regenerate Queries&quot; to start.
        </div>
      ) : (
        <div className="space-y-3">
          {checks.map((check) => (
            <div
              key={check.id}
              className={`bg-white/5 border rounded-2xl p-5 transition-all ${check.is_verified ? "border-emerald-500/30" : "border-white/10"}`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    {check.is_verified && (
                      <span className="px-2 py-0.5 text-xs rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-semibold">
                        ✓ Verified
                      </span>
                    )}
                  </div>
                  <p className="text-white font-medium text-sm leading-relaxed">&quot;{check.query}&quot;</p>
                  <div className="mt-2">
                    <ConfidenceBar value={check.expected_confidence} />
                    <div className="text-xs text-white/40 mt-1">Expected confidence</div>
                  </div>

                  {check.is_verified && (
                    <div className="flex gap-3 mt-3 flex-wrap">
                      {[
                        { label: "ChatGPT", val: check.chatgpt_mentions },
                        { label: "Gemini", val: check.gemini_mentions },
                        { label: "Perplexity", val: check.perplexity_mentions },
                      ].map((ai) => (
                        <div key={ai.label} className="flex items-center gap-1.5 text-xs text-white/50">
                          <span>{ai.label}:</span>
                          <MentionBadge value={ai.val} />
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Verify Panel */}
                {!check.is_verified && (
                  <div className="shrink-0 space-y-2">
                    {["chatgpt", "gemini", "perplexity"].map((ai) => (
                      <div key={ai} className="flex items-center gap-2">
                        <span className="text-xs text-white/40 w-16 capitalize">{ai}</span>
                        <div className="flex gap-1">
                          {MENTION_OPTIONS.map((opt) => (
                            <button
                              key={opt}
                              onClick={() =>
                                setVerifyState((prev) => ({
                                  ...prev,
                                  [check.id]: { ...(prev[check.id] || {}), [ai]: opt },
                                }))
                              }
                              className={`px-2 py-0.5 text-xs rounded-lg border transition-all ${
                                verifyState[check.id]?.[ai as keyof typeof verifyState[string]] === opt
                                  ? opt === "YES"
                                    ? "bg-emerald-500/30 border-emerald-500/50 text-emerald-300"
                                    : opt === "NO"
                                    ? "bg-red-500/30 border-red-500/50 text-red-300"
                                    : "bg-amber-500/30 border-amber-500/50 text-amber-300"
                                  : "border-white/10 text-white/40 hover:border-white/30"
                              }`}
                            >
                              {opt}
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                    <button
                      onClick={() => handleVerify(check.id)}
                      disabled={verifyingId === check.id || !verifyState[check.id]}
                      className="w-full mt-1 px-3 py-1.5 rounded-xl bg-violet-600/40 hover:bg-violet-600 disabled:opacity-40 text-white text-xs font-semibold transition-all border border-violet-500/30"
                    >
                      {verifyingId === check.id ? "Saving…" : "Save Verification"}
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
