from __future__ import annotations

from dataclasses import dataclass

from backend.fetch_runtime import (
    extract_budget,
    extract_urls,
    get_fetch_agent_spec,
    infer_task_family,
    normalize_text,
    remove_urls,
)


@dataclass(frozen=True)
class ChatDecision:
    kind: str
    message: str
    task_family: str | None = None


def _word_count(text: str) -> int:
    return len([part for part in normalize_text(remove_urls(text)).split(" ") if part])


def _default_example_prompt(agent_slug: str) -> str:
    spec = get_fetch_agent_spec(agent_slug)
    return spec.example_prompts[0] if spec.example_prompts else spec.description


def _build_handoff_message(agent_slug: str, requested_task_family: str) -> str:
    spec = get_fetch_agent_spec(agent_slug)
    target_names = ", ".join(f"`{slug}`" for slug in spec.handoff_targets) or "`resale_copilot_agent`"
    return (
        f"{spec.name} is specialized for {spec.task_family.replace('_', ' ')} requests, "
        f"but this looks like {requested_task_family.replace('_', ' ')}.\n\n"
        f"Try {target_names} instead."
    )


def _build_clarification_message(agent_slug: str, detail: str) -> str:
    spec = get_fetch_agent_spec(agent_slug)
    return f"{spec.name} needs {detail}\n\nExample: {_default_example_prompt(agent_slug)}"


def decide_chat_request(agent_slug: str, user_text: str) -> ChatDecision:
    text = normalize_text(user_text)
    if not text:
        return ChatDecision(
            kind="clarify",
            message=_build_clarification_message(agent_slug, "a concrete request before it can run."),
        )

    requested_task_family = (
        infer_task_family("resale_copilot_agent", text)
        if agent_slug != "resale_copilot_agent"
        else infer_task_family(agent_slug, text)
    )
    spec = get_fetch_agent_spec(agent_slug)
    urls = extract_urls(text)
    word_count = _word_count(text)
    lower = text.lower()

    if spec.is_public and agent_slug != "resale_copilot_agent" and requested_task_family != spec.task_family:
        return ChatDecision(
            kind="handoff",
            task_family=requested_task_family,
            message=_build_handoff_message(agent_slug, requested_task_family),
        )

    if agent_slug == "vision_agent" and not urls and word_count < 2:
        return ChatDecision(
            kind="clarify",
            task_family=spec.task_family,
            message=_build_clarification_message(
                agent_slug,
                "either a short item description or an image URL for the item.",
            ),
        )

    if agent_slug == "pricing_agent" and not urls and word_count < 3:
        return ChatDecision(
            kind="clarify",
            task_family=spec.task_family,
            message=_build_clarification_message(
                agent_slug,
                "item details such as brand, item type, condition, and optional photo link.",
            ),
        )

    if agent_slug == "depop_listing_agent" and not urls and word_count < 3:
        return ChatDecision(
            kind="clarify",
            task_family=spec.task_family,
            message=_build_clarification_message(
                agent_slug,
                "the item details and any listing style instructions before it can draft a listing.",
            ),
        )

    if agent_slug == "resale_copilot_agent":
        if requested_task_family in {"buy_rank", "buy_negotiate"} and extract_budget(text) is None:
            return ChatDecision(
                kind="clarify",
                task_family=requested_task_family,
                message=_build_clarification_message(
                    agent_slug,
                    "a target budget for buy-side sourcing or negotiation.",
                ),
            )
        if requested_task_family in {"sell_identify", "sell_price", "sell_list"} and not urls and word_count < 2:
            return ChatDecision(
                kind="clarify",
                task_family=requested_task_family,
                message=_build_clarification_message(
                    agent_slug,
                    "a short description or image URL for the item you want help with.",
                ),
            )
        if "submit" in lower and "confirm" not in lower and requested_task_family == "sell_list":
            return ChatDecision(
                kind="clarify",
                task_family=requested_task_family,
                message=_build_clarification_message(
                    agent_slug,
                    "confirmation language plus the item details before it tries a live listing path.",
                ),
            )

    return ChatDecision(kind="execute", task_family=requested_task_family, message="")
