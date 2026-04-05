from __future__ import annotations

import sys

from backend.fetch_agents.builder import build_fetch_agent
from backend.fetch_runtime import get_fetch_agent_spec, list_fetch_agent_slugs


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv
    if len(args) != 2:
        available = ", ".join(list_fetch_agent_slugs())
        print(f"Usage: python -m backend.fetch_agents.launch <agent-slug>\nAvailable: {available}")
        return 1

    try:
        spec = get_fetch_agent_spec(args[1])
    except KeyError as exc:
        print(exc)
        return 1

    if not spec.is_launchable:
        print(f"{args[1]} is an internal agent and cannot be launched directly. Use resale_copilot_agent.")
        return 1

    try:
        agent = build_fetch_agent(args[1])
    except Exception as exc:
        print(exc)
        return 1

    agent.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
