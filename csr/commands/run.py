"""Run command: upload and launch a script on Cloud Shell."""

import os
import sys
from datetime import datetime

from csr import fixtures
from csr import gcloud


def run(nickname: str, script_path: str, script_args: list[str]) -> None:
    """Upload script and launch it in the background.

    Steps:
    1. Resolve nickname -> config name
    2. Upload script via scp
    3. Launch detached ssh process
    4. Write PID file
    5. Return immediately
    """
    # 1. Resolve nickname -> config name
    try:
        config_name = fixtures.resolve_nickname(nickname)
    except fixtures.NicknameNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Upload script via scp
    script_basename = os.path.basename(script_path)
    try:
        gcloud.scp_to_cloudshell(config_name, script_path, script_basename)
    except Exception as e:
        print(f"Error uploading script: {e}", file=sys.stderr)
        sys.exit(1)

    # 3. Build remote command string
    args_str = " ".join(script_args) if script_args else ""
    remote_command = f"bash ~/{script_basename} {args_str}".strip()

    # 4. Create log file path
    runs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "runs")
    os.makedirs(runs_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(runs_dir, f"{nickname}_{timestamp}.log")

    # 5. Launch detached process
    try:
        process = gcloud.launch_detached(config_name, remote_command, log_path)
    except Exception as e:
        print(f"Error launching script: {e}", file=sys.stderr)
        sys.exit(1)

    # 6. Write PID file
    fixtures.write_pid(nickname, process.pid)

    print(f"Started run for '{nickname}' (PID: {process.pid})")
    print(f"Log file: {log_path}")
