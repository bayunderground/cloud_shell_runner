"""Stop command: interrupt a running script on Cloud Shell."""

import os
import signal
import subprocess
import sys

from csr import fixtures


def stop(nickname: str) -> None:
    """Stop a running script for the given nickname.

    Two mechanisms:
    1. PID-kill: kill the local gcloud cloud-shell ssh process
    2. Stop-flag: touch ~/.stop_<nickname> on Cloud Shell (always runs)

    Steps:
    1. Resolve nickname -> config name
    2. Read PID file
    3. If no PID file: skip PID-kill, still run stop-flag
    4. If PID file exists: check liveness, send SIGTERM if live
    5. Always fire stop-flag via SSH
    6. Remove PID file
    """
    # 1. Resolve nickname -> config name
    try:
        config_name = fixtures.resolve_nickname(nickname)
    except fixtures.NicknameNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Read PID file
    pid = fixtures.read_pid(nickname)

    # 3-4. PID-kill path (if PID file exists)
    if pid is not None:
        try:
            os.kill(pid, 0)  # Check if process exists (doesn't send signal)
            # Process is live, send SIGTERM
            os.kill(pid, signal.SIGTERM)
            print(f"Sent termination signal to PID {pid}")
        except ProcessLookupError:
            # Process doesn't exist anymore
            print(f"PID {pid} is no longer running")
        except PermissionError:
            print(f"Permission denied to signal PID {pid}", file=sys.stderr)

    # 5. Stop-flag path (ALWAYS runs, regardless of PID-kill outcome)
    try:
        subprocess.run(
            [
                "gcloud",
                "cloud-shell",
                "ssh",
                f"--configuration={config_name}",
                f"--command=touch ~/.stop_{nickname}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"Set stop flag ~/.stop_{nickname} on Cloud Shell")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not set stop flag: {e.stderr}", file=sys.stderr)

    # 6. Remove PID file (if it existed)
    if pid is not None:
        fixtures.remove_pid(nickname)
        print(f"Removed PID file for '{nickname}'")
