"""Thin wrappers around gcloud subprocess calls."""

import subprocess
import sys


def configuration_exists(name: str) -> bool:
    """Check if a gcloud named configuration exists.

    Returns True if the configuration exists, False otherwise.
    """
    result = subprocess.run(
        ["gcloud", "config", "configurations", "describe", name],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def auth_login(config_name: str) -> None:
    """Run gcloud auth login with the given configuration.

    This is interactive - lets stdio inherit so the browser flow works.
    """
    subprocess.run(
        ["gcloud", "auth", "login", f"--configuration={config_name}"],
        check=True,
    )


def scp_to_cloudshell(config_name: str, local_path: str, remote_filename: str) -> None:
    """Upload a file to Cloud Shell via scp."""
    # Placeholder for Step 3
    raise NotImplementedError


def launch_detached(config_name: str, remote_command: str, log_path: str):
    """Launch a detached gcloud cloud-shell ssh process."""
    # Placeholder for Step 3
    raise NotImplementedError
