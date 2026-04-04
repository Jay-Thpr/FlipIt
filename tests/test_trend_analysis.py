"""Tests for market trend + sell velocity analysis (Topic 4).

Tests compute_trend, compute_velocity, PricingOutput schema with
trend/velocity fields, and PricingAgent output integration.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from backend.agents.trend_analysis import compute_trend, compute_velocity
from backend.schemas import PricingOutput, TrendData, VelocityData


def _make_comps(prices_recent: list[float], prices_older: list[float]) -> list[dict]:
    """Build a comp list with recent (<30 days) and older (30-90 days) prices."""
    now = datetime.now(timezone.utc)
    comps = []
    for price in prices_recent:
        date = (now - timedelta(days=5)).date().isoformat()
        comps.append({"price": price, "date_sold": date})
    for price in prices_older:
        date = (now - timedelta(days=50)).date().isoformat()
        comps.append({"price": price, "date_sold": date})
    return comps


class TestComputeTrend:
    def test_rising(self):
        comps = _make_comps([60.0, 65.0, 70.0], [40.0, 45.0, 50.0])
        result = compute_trend(comps)
        assert result["trend"] == "rising"
        assert result["delta_pct"] > 5

    def test_falling(self):
        comps = _make_comps([30.0, 35.0, 32.0], [50.0, 55.0, 60.0])
        result = compute_trend(comps)
        assert result["trend"] == "falling"
        assert result["delta_pct"] < -5

    def test_stable(self):
        comps = _make_comps([50.0, 51.0, 49.0], [50.0, 50.0, 50.0])
        result = compute_trend(comps)
        assert result["trend"] == "stable"
        assert -5 <= result["delta_pct"] <= 5

    def test_insufficient_data(self):
        comps = _make_comps([50.0], [])  # only 1 recent, 0 older
        result = compute_trend(comps)
        assert result["trend"] == "neutral"
        assert result["signal"] == "Insufficient data"


class TestComputeVelocity:
    def test_high(self):
        now = datetime.now(timezone.utc)
        comps = [
            {"price": 50.0, "date_sold": (now - timedelta(days=i)).date().isoformat()}
            for i in range(10)
        ]
        result = compute_velocity(comps)
        assert result["velocity"] == "high"
        assert result["sold_last_30_days"] == 10

    def test_medium(self):
        now = datetime.now(timezone.utc)
        recent = [{"price": 50.0, "date_sold": (now - timedelta(days=5)).date().isoformat()} for _ in range(4)]
        old = [{"price": 50.0, "date_sold": (now - timedelta(days=60)).date().isoformat()} for _ in range(6)]
        result = compute_velocity(recent + old)
        assert result["velocity"] == "medium"

    def test_low(self):
        now = datetime.now(timezone.utc)
        recent = [{"price": 50.0, "date_sold": (now - timedelta(days=5)).date().isoformat()} for _ in range(1)]
        old = [{"price": 50.0, "date_sold": (now - timedelta(days=60)).date().isoformat()} for _ in range(9)]
        result = compute_velocity(recent + old)
        assert result["velocity"] == "low"

    def test_empty_comps(self):
        result = compute_velocity([])
        assert result["velocity"] == "low"
        assert result["total_comps"] == 0


class TestPricingSchemaWithTrend:
    def test_accepts_trend_and_velocity(self):
        output = PricingOutput(
            agent="pricing_agent",
            display_name="Pricing Agent",
            summary="Priced item at $50",
            recommended_list_price=50.0,
            expected_profit=20.0,
            pricing_confidence=0.85,
            trend=TrendData(
                trend="rising",
                delta_pct=12.5,
                recent_median=55.0,
                older_median=48.0,
                signal="↑ Up 12.5% last 30 days",
            ),
            velocity=VelocityData(
                velocity="high",
                label="High demand",
                detail="Selling fast",
                sold_last_30_days=8,
                total_comps=10,
            ),
        )
        assert output.trend is not None
        assert output.velocity is not None
        assert output.trend.trend == "rising"
        assert output.velocity.velocity == "high"

    def test_accepts_none_trend_and_velocity(self):
        output = PricingOutput(
            agent="pricing_agent",
            display_name="Pricing Agent",
            summary="Priced item at $50",
            recommended_list_price=50.0,
            expected_profit=20.0,
            pricing_confidence=0.85,
        )
        assert output.trend is None
        assert output.velocity is None


class TestPricingAgentOutput:
    def test_output_includes_trend_and_velocity(self):
        from backend.agents.pricing_agent import agent
        from backend.schemas import AgentTaskRequest

        request = AgentTaskRequest(
            session_id="test-session",
            pipeline="sell",
            step="pricing",
            input={
                "original_input": {"image_urls": [], "notes": "Nike hoodie"},
                "previous_outputs": {
                    "vision_analysis": {
                        "agent": "vision_agent",
                        "display_name": "Vision Agent",
                        "summary": "Inferred Nike hoodie",
                        "detected_item": "hoodie",
                        "brand": "Nike",
                        "category": "apparel",
                        "condition": "good",
                    },
                    "ebay_sold_comps": {
                        "agent": "ebay_sold_comps_agent",
                        "display_name": "eBay Sold Comps Agent",
                        "summary": "12 sold comps",
                        "median_sold_price": 55.0,
                        "low_sold_price": 30.0,
                        "high_sold_price": 80.0,
                        "sample_size": 12,
                        "execution_mode": "fallback",
                        "browser_use_error": None,
                        "browser_use": None,
                    },
                },
            },
        )
        result = asyncio.run(agent.build_output(request))
        assert "trend" in result
        assert "velocity" in result
        assert result["trend"]["trend"] in {"rising", "falling", "stable", "neutral"}
        assert result["velocity"]["velocity"] in {"high", "medium", "low"}
