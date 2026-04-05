from __future__ import annotations

from typing import Any

from backend.schemas import SessionEvent, SessionState

BUY_SEARCH_STEPS = ("depop_search", "ebay_search", "mercari_search", "offerup_search")
SELL_MODE_STEPS = ("ebay_sold_comps", "depop_listing")
PROGRESS_EVENT_TYPES = {"agent_started", "agent_retrying", "agent_completed"}


def get_session_item_id(session: SessionState) -> str | None:
    item_id = session.request.metadata.get("item_id")
    if item_id is None:
        return None
    return str(item_id)


def build_run_start_response(
    *,
    payload: dict[str, Any],
    item_id: str | None,
    run_url: str,
) -> dict[str, Any]:
    response = dict(payload)
    response["run_id"] = payload["session_id"]
    response["run_url"] = run_url
    response["item_id"] = item_id
    response["phase"] = "queued"
    response["next_action"] = {"type": "wait", "payload": {}}
    response["progress"] = None
    response["result_source"] = None
    return response


def build_run_payload(session: SessionState) -> dict[str, Any]:
    payload = session.model_dump()
    payload["run_id"] = session.session_id
    payload["item_id"] = get_session_item_id(session)
    payload["phase"] = derive_phase(session)
    payload["next_action"] = derive_next_action(session)
    payload["progress"] = derive_progress(session)
    payload["result_source"] = derive_result_source(session)
    if session.pipeline == "sell":
        payload.update(build_sell_summary(session))
    if session.pipeline == "buy":
        payload.update(build_buy_summary(session))
    return payload


def derive_phase(session: SessionState) -> str:
    if session.status == "paused":
        if session.sell_listing_review is not None:
            return "awaiting_listing_review"
        return "awaiting_user_correction"
    return {
        "queued": "queued",
        "running": "running",
        "completed": "completed",
        "failed": "failed",
    }[session.status]


def derive_next_action(session: SessionState) -> dict[str, Any]:
    if session.status in {"queued", "running"}:
        return {"type": "wait", "payload": {}}
    if session.status == "completed":
        return {"type": "show_result", "payload": {}}
    if session.status == "failed":
        return {"type": "show_error", "payload": {"error": session.error}}
    if session.sell_listing_review is not None:
        listing_output = _get_outputs(session).get("depop_listing", {})
        return {
            "type": "review_listing",
            "payload": {
                "allowed_decisions": ["confirm_submit", "revise", "abort"],
                "review_state": session.sell_listing_review.model_dump(),
                "listing": listing_output,
            },
        }

    pause_event = _latest_event(session, "vision_low_confidence")
    return {
        "type": "submit_correction",
        "payload": {
            "message": pause_event.data.get("message") if pause_event is not None else None,
            "suggestion": _get_outputs(session).get("vision_analysis"),
        },
    }


def derive_progress(session: SessionState) -> dict[str, Any] | None:
    if session.status == "paused":
        if session.sell_listing_review is not None:
            return {
                "step": "depop_listing",
                "event_type": "listing_review_required",
            }
        pause_event = _latest_event(session, "vision_low_confidence")
        if pause_event is not None:
            return {
                "step": pause_event.step or "vision_analysis",
                "event_type": pause_event.event_type,
            }

    event = _latest_progress_event(session)
    if event is not None:
        return {
            "step": event.step,
            "event_type": event.event_type,
        }

    outputs = _get_outputs(session)
    if outputs:
        last_step = next(reversed(outputs))
        return {"step": last_step, "event_type": "agent_completed"}
    return None


def build_sell_summary(session: SessionState) -> dict[str, Any]:
    outputs = _get_outputs(session)
    vision = outputs.get("vision_analysis", {}) if isinstance(outputs.get("vision_analysis"), dict) else {}
    pricing = outputs.get("pricing", {}) if isinstance(outputs.get("pricing"), dict) else {}
    listing = outputs.get("depop_listing", {}) if isinstance(outputs.get("depop_listing"), dict) else {}

    return {
        "sell_summary": {
            "detected_item": vision.get("detected_item"),
            "brand": vision.get("brand"),
            "confidence": vision.get("confidence"),
            "recommended_price": pricing.get("recommended_list_price"),
            "listing_title": listing.get("title"),
            "listing_price": listing.get("suggested_price"),
            "listing_status": listing.get("listing_status"),
            "ready_for_confirmation": bool(listing.get("ready_for_confirmation", False)),
        }
    }


def derive_result_source(session: SessionState) -> str | None:
    outputs = _get_outputs(session)
    if session.pipeline == "buy":
        modes = [outputs.get(step, {}).get("execution_mode") for step in BUY_SEARCH_STEPS if isinstance(outputs.get(step), dict)]
    else:
        modes = [outputs.get(step, {}).get("execution_mode") for step in SELL_MODE_STEPS if isinstance(outputs.get(step), dict)]

    normalized = {mode for mode in modes if isinstance(mode, str) and mode}
    if not normalized:
        return None
    if len(normalized) == 1:
        return next(iter(normalized))
    return "mixed"


def build_buy_summary(session: SessionState) -> dict[str, Any]:
    outputs = _get_outputs(session)
    search_outputs = {
        step: outputs.get(step, {})
        for step in BUY_SEARCH_STEPS
        if isinstance(outputs.get(step), dict)
    }
    results_by_platform = {
        step.removesuffix("_search"): len(platform_output.get("results", []))
        for step, platform_output in search_outputs.items()
    }
    failed_steps = {
        event.step
        for event in session.events
        if event.event_type == "agent_error" and event.step in BUY_SEARCH_STEPS
    }

    ranking = outputs.get("ranking", {}) if isinstance(outputs.get("ranking"), dict) else {}
    negotiation = outputs.get("negotiation", {}) if isinstance(outputs.get("negotiation"), dict) else {}
    offers = negotiation.get("offers", []) if isinstance(negotiation.get("offers"), list) else []
    sent_offers = [offer for offer in offers if offer.get("status") == "sent"]
    best_offer = min(sent_offers, key=lambda offer: float(offer.get("target_price", 0.0)), default=None)

    return {
        "search_summary": {
            "total_results": sum(results_by_platform.values()),
            "results_by_platform": results_by_platform,
            "platforms_searched": sum(1 for count in results_by_platform.values() if count > 0),
            "platforms_failed": len(failed_steps),
            "median_price": ranking.get("median_price"),
        },
        "top_choice": ranking.get("top_choice"),
        "offer_summary": {
            "total_offers": len(offers),
            "offers_sent": len(sent_offers),
            "offers_failed": sum(1 for offer in offers if offer.get("status") == "failed"),
            "offers": offers,
            "best_offer": best_offer,
        },
    }


def _get_outputs(session: SessionState) -> dict[str, Any]:
    result = session.result if isinstance(session.result, dict) else {}
    outputs = result.get("outputs", {})
    return outputs if isinstance(outputs, dict) else {}


def _latest_progress_event(session: SessionState) -> SessionEvent | None:
    for event in reversed(session.events):
        if event.step and event.event_type in PROGRESS_EVENT_TYPES:
            return event
    return None


def _latest_event(session: SessionState, event_type: str) -> SessionEvent | None:
    for event in reversed(session.events):
        if event.event_type == event_type:
            return event
    return None
