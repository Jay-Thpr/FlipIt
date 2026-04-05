"""Market trend and sell velocity analysis.

Pure functions — no external API calls. Operates on sold-comp data
already available from EbaySoldCompsAgent. Based on DerrekPlan §3.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import median

from dateutil import parser as dateparser


def _parse_date(date_str: str) -> datetime:
    """Best-effort date parsing with fallback to 45 days ago."""
    try:
        dt = dateparser.parse(date_str)
        if dt is None:
            return datetime.now(timezone.utc) - timedelta(days=45)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc) - timedelta(days=45)


def compute_trend(comps: list[dict]) -> dict:
    """Compare recent (last 30 days) vs older (30–90 days) median prices.

    Returns: { trend, delta_pct, recent_median, older_median, signal }
    """
    now = datetime.now(timezone.utc)
    cutoff_30 = now - timedelta(days=30)
    cutoff_90 = now - timedelta(days=90)

    recent = [c["price"] for c in comps if _parse_date(c["date_sold"]) > cutoff_30]
    older = [c["price"] for c in comps if cutoff_90 < _parse_date(c["date_sold"]) <= cutoff_30]

    if len(recent) < 2 or len(older) < 2:
        return {
            "trend": "neutral",
            "delta_pct": 0.0,
            "recent_median": 0.0,
            "older_median": 0.0,
            "signal": "Insufficient data",
        }

    recent_median = median(recent)
    older_median = median(older)

    if older_median == 0:
        return {
            "trend": "neutral",
            "delta_pct": 0.0,
            "recent_median": round(recent_median, 2),
            "older_median": 0.0,
            "signal": "Insufficient data",
        }

    delta_pct = ((recent_median - older_median) / older_median) * 100

    if delta_pct > 5:
        trend = "rising"
        signal = f"↑ Up {delta_pct:.1f}% last 30 days"
    elif delta_pct < -5:
        trend = "falling"
        signal = f"↓ Down {abs(delta_pct):.1f}% last 30 days"
    else:
        trend = "stable"
        signal = f"→ Stable (±{abs(delta_pct):.1f}%)"

    return {
        "trend": trend,
        "delta_pct": round(delta_pct, 1),
        "recent_median": round(recent_median, 2),
        "older_median": round(older_median, 2),
        "signal": signal,
    }


def compute_velocity(comps: list[dict]) -> dict:
    """How fast is this item selling? Based on recency of sold listings.

    Returns: { velocity, label, detail, sold_last_30_days, total_comps }
    """
    if not comps:
        return {
            "velocity": "low",
            "label": "Low demand",
            "detail": "No comparable sales data",
            "sold_last_30_days": 0,
            "total_comps": 0,
        }

    now = datetime.now(timezone.utc)
    cutoff_30 = now - timedelta(days=30)
    last_30 = sum(1 for c in comps if _parse_date(c["date_sold"]) > cutoff_30)
    ratio = last_30 / len(comps)

    if ratio > 0.6:
        label = "High demand"
        detail = "Selling fast"
        velocity = "high"
    elif ratio > 0.3:
        label = "Moderate demand"
        detail = "Moving steadily"
        velocity = "medium"
    else:
        label = "Low demand"
        detail = "Slow mover"
        velocity = "low"

    return {
        "velocity": velocity,
        "label": label,
        "detail": detail,
        "sold_last_30_days": last_30,
        "total_comps": len(comps),
    }
