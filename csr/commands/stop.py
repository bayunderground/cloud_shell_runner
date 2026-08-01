"""Stop command: interrupt a running script on Cloud Shell."""

import os
import signal
import sys

from csr import fixtures


def stop(nickname: str) -> None:
    """Stop a running script for the given nickname.

    PID-kill path only (Step 4). Stop-flag path added in Step 5.

    Steps:
    1. Resolve nickname -> config name
    2. Read PID file
    3. If no PID file: print message, exit 0 (clean no-op)
    4. If PID file exists: check liveness, send SIGTERM if live
    5. Remove PID file
    """
    # 1. Resolve nickname -> config name (for future use in Step 5)
    try:
        config_name = fixtures.resolve_nickname(nickname)
    except fixtures.NicknameNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Read PID file
    pid = fixtures.read_pid(nickname)

    # 3. If no PID file: clean no-op
    if pid is None:
        print(f"No in-progress run for '{nickname}'")
        return

    # 4. Check if PID is live and send termination signal
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

    # 5. Remove PID file
    fixtures.remove_pid(nickname)
    print(f"Removed PID file for '{nickname}'")
