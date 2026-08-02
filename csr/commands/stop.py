"""Stop command: interrupt a running script on Cloud Shell."""

import os
import signal
import subprocess
import sys

from csr import fixtures
from csr import gcloud


def stop(nickname: str) -> None:
    """Stop a running script for the given nickname.

    Three mechanisms:
    1. Local PID-kill: kill the local gcloud cloud-shell ssh process
    2. Remote PID-kill: kill the remote script process on Cloud Shell
    3. Stop-flag: touch ~/.stop_<nickname> on Cloud Shell (always runs)

    Steps:
    1. Resolve nickname -> config name
    2. Kill local PID if live
    3. Kill remote PID if live
    4. Always set stop-flag
    5. Remove local PID file
    """
    # 1. Resolve nickname -> config name
    try:
        config_name = fixtures.resolve_nickname(nickname)
    except fixtures.NicknameNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Kill local PID (if PID file exists)
    pid = fixtures.read_pid(nickname)
    if pid is not None:
        try:
            os.kill(pid, 0)  # Check if process exists (doesn't send signal)
            # Process is live, send SIGTERM
            os.kill(pid, signal.SIGTERM)
            print(f"Sent termination signal to local PID {pid}")
        except ProcessLookupError:
            print(f"Local PID {pid} is no longer running")
        except PermissionError:
            print(f"Permission denied to signal local PID {pid}", file=sys.stderr)

    # 3. Kill remote PID via SSH
    try:
        if gcloud.kill_remote_pid(config_name, nickname):
            print(f"Killed remote process for '{nickname}'")
        else:
            print(f"No remote process found for '{nickname}'")
    except Exception as e:
        print(f"Warning: Could not kill remote process: {e}", file=sys.stderr)

    # 4. Stop-flag path (ALWAYS runs, regardless of other outcomes)
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

    # 5. Remove PID files (if they existed)
    if pid is not None:
        fixtures.remove_pid(nickname)
        print(f"Removed local PID file for '{nickname}'")
    fixtures.remove_remote_pid(nickname)
