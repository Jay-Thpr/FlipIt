from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

from backend.config import AGENTS


def main() -> int:
    processes: list[subprocess.Popen] = []
    try:
        for agent in AGENTS:
            module = f"backend.agents.{agent.slug}:app"
            command = [
                sys.executable,
                "-m",
                "uvicorn",
                module,
                "--host",
                "0.0.0.0",
                "--port",
                str(agent.port),
            ]
            env = os.environ.copy()
            env["PYTHONPATH"] = os.getcwd()
            processes.append(subprocess.Popen(command, env=env))
            print(f"Started {agent.slug} on port {agent.port}")
            time.sleep(0.15)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping agent processes...")
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
