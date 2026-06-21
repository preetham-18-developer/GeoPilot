"""
historical_tracker.py

HistoricalTracker — longitudinal performance tracking engine.

NO LLM calls. Pure metric aggregation and trend analysis.

Tracks across analysis runs:
  - visibility_score
  - recommendation_score
  - hallucination_score  (inverted hallucination_risk_score)
  - consistency_score
  - coverage_score

Computes:
  - weekly trend (last 7 days vs previous 7 days)
  - monthly trend (last 30 days vs previous 30 days)
  - velocity (average delta over last 3 runs)
  - improvement flags
  - regression warnings (score dropped >= 10 points)
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta


def _avg(values: list) -> float:
    return sum(values) / len(values) if values else 0.0


def _trend_direction(delta: float) -> str:
    if delta > 3:
        return "improving"
    if delta < -3:
        return "declining"
    return "stable"


class HistoricalTracker:
    """
    Tracks and analyzes longitudinal score history for a project.
    """

    SCORE_KEYS = [
        "visibility_score",
        "recommendation_score",
        "hallucination_score",
        "consistency_score",
        "coverage_score",
    ]

    def build_run_record(
        self,
        project_id: str,
        run_id: str,
        visibility_score: float = 0.0,
        recommendation_score: float = 0.0,
        hallucination_risk_score: float = 0.0,
        consistency_score: float = 0.0,
        coverage_score: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Produces a clean record dict ready for insertion into historical_metrics.
        hallucination_score is inverted (100 - risk_score) so higher is better.
        """
        return {
            "project_id": project_id,
            "run_id": run_id,
            "visibility_score": round(float(visibility_score), 1),
            "recommendation_score": round(float(recommendation_score), 1),
            "hallucination_score": round(max(0.0, 100.0 - float(hallucination_risk_score)), 1),
            "consistency_score": round(float(consistency_score), 1),
            "coverage_score": round(float(coverage_score), 1),
        }

    def calculate_trends(self, historical_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Given a list of historical_metrics rows (sorted by created_at ascending),
        returns trend analytics, velocity, and regression warnings.
        """
        if not historical_rows:
            return {
                "total_runs": 0,
                "runs": [],
                "trends": {},
                "regression_warnings": [],
                "improvement_flags": [],
            }

        rows = sorted(historical_rows, key=lambda r: r.get("created_at", ""))
        now_str = datetime.now(timezone.utc).isoformat()

        def _parse_ts(row: Dict) -> Optional[datetime]:
            ts = row.get("created_at")
            if not ts:
                return None
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                return None

        now_dt = datetime.now(timezone.utc)
        week_ago = now_dt - timedelta(days=7)
        two_weeks_ago = now_dt - timedelta(days=14)
        month_ago = now_dt - timedelta(days=30)
        two_months_ago = now_dt - timedelta(days=60)

        def _score_window(rows, start_dt, end_dt) -> List[Dict]:
            result = []
            for r in rows:
                ts = _parse_ts(r)
                if ts and start_dt <= ts <= end_dt:
                    result.append(r)
            return result

        recent_week = _score_window(rows, week_ago, now_dt)
        prev_week = _score_window(rows, two_weeks_ago, week_ago)
        recent_month = _score_window(rows, month_ago, now_dt)
        prev_month = _score_window(rows, two_months_ago, month_ago)

        trends = {}
        for key in self.SCORE_KEYS:
            rw_vals = [float(r.get(key, 0) or 0) for r in recent_week]
            pw_vals = [float(r.get(key, 0) or 0) for r in prev_week]
            rm_vals = [float(r.get(key, 0) or 0) for r in recent_month]
            pm_vals = [float(r.get(key, 0) or 0) for r in prev_month]

            weekly_delta = round(_avg(rw_vals) - _avg(pw_vals), 1) if (rw_vals and pw_vals) else 0.0
            monthly_delta = round(_avg(rm_vals) - _avg(pm_vals), 1) if (rm_vals and pm_vals) else 0.0

            # Velocity: avg delta between consecutive last-3 runs
            last_3 = [float(r.get(key, 0) or 0) for r in rows[-3:]]
            if len(last_3) >= 2:
                deltas = [last_3[i + 1] - last_3[i] for i in range(len(last_3) - 1)]
                velocity = round(_avg(deltas), 1)
            else:
                velocity = 0.0

            current_val = float(rows[-1].get(key, 0) or 0) if rows else 0.0
            trends[key] = {
                "current": current_val,
                "weekly_delta": weekly_delta,
                "weekly_direction": _trend_direction(weekly_delta),
                "monthly_delta": monthly_delta,
                "monthly_direction": _trend_direction(monthly_delta),
                "velocity": velocity,
                "velocity_direction": _trend_direction(velocity),
            }

        # ── Regression Warnings (score dropped >= 10 points vs previous run) ────
        regression_warnings = []
        if len(rows) >= 2:
            prev = rows[-2]
            curr = rows[-1]
            for key in self.SCORE_KEYS:
                prev_val = float(prev.get(key, 0) or 0)
                curr_val = float(curr.get(key, 0) or 0)
                drop = prev_val - curr_val
                if drop >= 10:
                    regression_warnings.append({
                        "metric": key.replace("_", " ").title(),
                        "previous": prev_val,
                        "current": curr_val,
                        "drop": round(drop, 1),
                        "severity": "critical" if drop >= 20 else "warning",
                    })

        # ── Improvement Flags ─────────────────────────────────────────────────
        improvement_flags = []
        if len(rows) >= 2:
            first = rows[0]
            latest = rows[-1]
            for key in self.SCORE_KEYS:
                start_val = float(first.get(key, 0) or 0)
                end_val = float(latest.get(key, 0) or 0)
                gain = end_val - start_val
                if gain >= 10:
                    improvement_flags.append({
                        "metric": key.replace("_", " ").title(),
                        "start": start_val,
                        "current": end_val,
                        "gain": round(gain, 1),
                    })

        return {
            "total_runs": len(rows),
            "runs": [
                {
                    "created_at": r.get("created_at", ""),
                    "visibility_score": float(r.get("visibility_score", 0) or 0),
                    "recommendation_score": float(r.get("recommendation_score", 0) or 0),
                    "hallucination_score": float(r.get("hallucination_score", 0) or 0),
                    "consistency_score": float(r.get("consistency_score", 0) or 0),
                    "coverage_score": float(r.get("coverage_score", 0) or 0),
                }
                for r in rows
            ],
            "trends": trends,
            "regression_warnings": regression_warnings,
            "improvement_flags": improvement_flags,
        }
