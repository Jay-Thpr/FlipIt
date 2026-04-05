from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass, field

from dotenv import load_dotenv


def _import_uagents():
    from uagents import Agent, Context, Protocol
    from uagents_core.contrib.protocols.chat import (
        ChatAcknowledgement,
        ChatMessage,
        EndSessionContent,
        TextContent,
    )

    return Agent, Context, Protocol, ChatAcknowledgement, ChatMessage, EndSessionContent, TextContent


@dataclass
class DemoState:
    response_text: str | None = None
    acknowledgement_received: bool = False
    done: asyncio.Event = field(default_factory=asyncio.Event)


async def run_demo(
    *,
    destination: str,
    message: str,
    timeout: float,
    startup_delay: float,
    seed: str,
    port: int,
) -> str:
    (
        Agent,
        Context,
        Protocol,
        ChatAcknowledgement,
        ChatMessage,
        EndSessionContent,
        TextContent,
    ) = _import_uagents()

    state = DemoState()
    client = Agent(
        name="FetchDemoClient",
        seed=seed,
        port=port,
        mailbox=True,
        publish_agent_details=False,
    )
    protocol = Protocol()

    @client.on_event("startup")
    async def send_chat(ctx: Context) -> None:
        await asyncio.sleep(startup_delay)
        await ctx.send(
            destination,
            ChatMessage(
                content=[TextContent(type="text", text=message)],
            ),
        )

    @protocol.on_message(ChatAcknowledgement)
    async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement) -> None:
        del ctx, sender, msg
        state.acknowledgement_received = True

    @protocol.on_message(ChatMessage)
    async def handle_chat(ctx: Context, sender: str, msg: ChatMessage) -> None:
        del ctx, sender
        text_parts: list[str] = []
        saw_end_session = False
        for content in msg.content:
            text = getattr(content, "text", None)
            if isinstance(text, str):
                text_parts.append(text)
            if isinstance(content, EndSessionContent):
                saw_end_session = True
        if text_parts:
            state.response_text = "\n".join(text_parts).strip()
        if saw_end_session:
            state.done.set()

    client.include(protocol)
    task = asyncio.create_task(client.run_async())
    try:
        await asyncio.wait_for(state.done.wait(), timeout=timeout)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    if state.response_text is None:
        raise RuntimeError("Fetch agent ended the chat without returning text content.")

    return state.response_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a ChatMessage to a running Fetch/Agentverse agent and print the response.",
    )
    parser.add_argument("--address", required=True, help="Destination Agentverse agent address (agent1q...).")
    parser.add_argument("--message", required=True, help="Chat prompt to send to the fetch agent.")
    parser.add_argument(
        "--timeout",
        type=float,
        default=45.0,
        help="Seconds to wait for the end-session ChatMessage response.",
    )
    parser.add_argument(
        "--startup-delay",
        type=float,
        default=2.0,
        help="Seconds to wait before the demo client sends the first message.",
    )
    parser.add_argument(
        "--seed",
        default="fetch-demo-client-seed",
        help="Seed for the temporary mailbox-enabled demo client.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9300,
        help="Local port for the temporary demo client agent.",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()
    response = asyncio.run(
        run_demo(
            destination=args.address,
            message=args.message,
            timeout=args.timeout,
            startup_delay=args.startup_delay,
            seed=args.seed,
            port=args.port,
        )
    )
    print(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
