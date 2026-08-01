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
    """Upload a file to Cloud Shell via scp.

    Uses cloudshell:/localhost: path prefixes per gcloud conventions.
    """
    subprocess.run(
        [
            "gcloud",
            "cloud-shell",
            "scp",
            f"--configuration={config_name}",
            f"localhost:{local_path}",
            f"cloudshell:~/{remote_filename}",
        ],
        check=True,
    )


def launch_detached(config_name: str, remote_command: str, log_path: str) -> subprocess.Popen:
    """Launch a detached gcloud cloud-shell ssh process.

    Returns Popen object without blocking. Stdout/stderr redirected to log_path.
    """
    with open(log_path, "w") as log_file:
        process = subprocess.Popen(
            [
                "gcloud",
                "cloud-shell",
                "ssh",
                f"--configuration={config_name}",
                "--authorize-session",
                f"--command={remote_command}",
            ],
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
    return process
