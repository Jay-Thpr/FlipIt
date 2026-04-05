from __future__ import annotations

import argparse
import asyncio
import json
from uuid import uuid4

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a chat-style request to a running local Fetch agent.")
    parser.add_argument("port", type=int, help="Local Fetch agent port, for example 9205")
    parser.add_argument("message", help="Message text to send to the agent")
    parser.add_argument("--host", default="127.0.0.1", help="Local Fetch agent host")
    return parser.parse_args()


def build_payload(message: str) -> dict[str, object]:
    return {
        "type": "ChatMessage",
        "timestamp": None,
        "msg_id": str(uuid4()),
        "content": [
            {
                "type": "text",
                "text": message,
            }
        ],
    }


async def main() -> int:
    args = parse_args()
    payload = build_payload(args.message)
    url = f"http://{args.host}:{args.port}/submit"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
    print(json.dumps(response.json(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
