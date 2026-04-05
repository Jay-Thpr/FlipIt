from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

from backend.config import assert_fetch_agent_ports_do_not_overlap
from backend.fetch_runtime import list_fetch_agent_slugs


def main() -> int:
    assert_fetch_agent_ports_do_not_overlap()
    processes: list[subprocess.Popen] = []
    try:
        for agent_slug in list_fetch_agent_slugs():
            command = [
                sys.executable,
                "-m",
                "backend.fetch_agents.launch",
                agent_slug,
            ]
            env = os.environ.copy()
            env["PYTHONPATH"] = os.getcwd()
            processes.append(subprocess.Popen(command, env=env))
            print(f"Started Fetch agent {agent_slug}")
            time.sleep(0.2)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping Fetch agents...")
    finally:
        for process in processes:
            if process.poll() is None:
                process.send_signal(signal.SIGTERM)
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
