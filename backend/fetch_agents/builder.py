from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.fetch_agents.chat_profiles import decide_chat_request
from backend.fetch_runtime import format_fetch_response, get_fetch_agent_spec, run_fetch_query


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _import_uagents() -> tuple[Any, Any, Any, Any, Any, Any, Any, Any]:
    try:
        from uagents import Agent, Context, Protocol
        from uagents_core.contrib.protocols.chat import (
            ChatAcknowledgement,
            ChatMessage,
            EndSessionContent,
            TextContent,
            chat_protocol_spec,
        )
    except Exception as exc:
        raise RuntimeError(
            "Fetch agents could not import the uAgents runtime. "
            "In this environment, uagents 0.24.0 is not compatible with Python 3.14. "
            "Use Python 3.12 or 3.13 for the Fetch agent processes."
        ) from exc

    return Agent, Context, Protocol, ChatAcknowledgement, ChatMessage, EndSessionContent, TextContent, chat_protocol_spec


def _extract_text(msg: Any) -> str:
    parts: list[str] = []
    for item in msg.content:
        text = getattr(item, "text", None)
        if isinstance(text, str):
            parts.append(text)
    return " ".join(parts).strip()


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _build_agent_metadata(spec: Any) -> dict[str, object]:
    return {
        "description": spec.description,
        "persona": spec.persona,
        "capabilities": list(spec.capabilities),
        "example_prompts": list(spec.example_prompts),
        "tags": list(spec.tags),
        "task_family": spec.task_family,
        "is_public": spec.is_public,
        "handoff_targets": list(spec.handoff_targets),
    }


def _instantiate_agent(agent_cls: Any, agent_kwargs: dict[str, Any], spec: Any) -> Any:
    enriched_kwargs = dict(agent_kwargs)
    enriched_kwargs["metadata"] = _build_agent_metadata(spec)
    if spec.readme_path:
        enriched_kwargs["readme_path"] = spec.readme_path
    try:
        return agent_cls(**enriched_kwargs)
    except TypeError:
        return agent_cls(**agent_kwargs)


def build_fetch_agent(agent_slug: str) -> Any:
    try:
        spec = get_fetch_agent_spec(agent_slug)
    except KeyError as exc:
        raise ValueError(f"Unknown Fetch agent slug: {agent_slug}") from exc

    (
        Agent,
        Context,
        Protocol,
        ChatAcknowledgement,
        ChatMessage,
        EndSessionContent,
        TextContent,
        chat_protocol_spec,
    ) = _import_uagents()

    seed = os.getenv(spec.seed_env_var)
    if not seed:
        raise RuntimeError(
            f"Missing {spec.seed_env_var}. Set it in your environment before starting {spec.name}."
        )

    agent_kwargs: dict[str, Any] = {
        "name": spec.name,
        "seed": seed,
        "port": spec.port,
        "mailbox": True,
        "publish_agent_details": True,
    }
    if _env_flag("FETCH_USE_LOCAL_ENDPOINT", default=False):
        agent_kwargs["endpoint"] = [f"http://127.0.0.1:{spec.port}/submit"]

    agent = _instantiate_agent(Agent, agent_kwargs, spec)
    protocol = Protocol(spec=chat_protocol_spec)

    @protocol.on_message(ChatMessage)
    async def handle_message(ctx: Context, sender: str, msg: ChatMessage) -> None:
        await ctx.send(
            sender,
            ChatAcknowledgement(
                timestamp=_utcnow(),
                acknowledged_msg_id=msg.msg_id,
            ),
        )

        user_text = _extract_text(msg)
        try:
            decision = decide_chat_request(agent_slug, user_text)
            if decision.kind == "execute":
                result = await run_fetch_query(agent_slug, user_text)
                response_text = format_fetch_response(agent_slug, user_text, result)
            else:
                response_text = decision.message
        except Exception as exc:
            ctx.logger.exception("Fetch agent execution failed")
            response_text = (
                f"{spec.name} could not complete the request.\n\n"
                f"Error: {exc}"
            )

        await ctx.send(
            sender,
            ChatMessage(
                timestamp=_utcnow(),
                msg_id=uuid4(),
                content=[
                    TextContent(type="text", text=response_text),
                    EndSessionContent(type="end-session"),
                ],
            ),
        )

    @protocol.on_message(ChatAcknowledgement)
    async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement) -> None:
        ctx.logger.debug("Acknowledgement received from %s for %s", sender, msg.acknowledged_msg_id)

    agent.include(protocol, publish_manifest=True)
    return agent
