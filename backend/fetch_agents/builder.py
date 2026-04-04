from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.fetch_runtime import FETCH_AGENT_SPECS, format_fetch_response, run_fetch_query


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


def build_fetch_agent(agent_slug: str) -> Any:
    try:
        spec = FETCH_AGENT_SPECS[agent_slug]
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

    agent = Agent(
        name=spec.name,
        seed=seed,
        port=spec.port,
        endpoint=[f"http://127.0.0.1:{spec.port}/submit"],
        mailbox=True,
        publish_agent_details=True,
    )
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
            result = await run_fetch_query(agent_slug, user_text)
            response_text = format_fetch_response(agent_slug, user_text, result)
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
