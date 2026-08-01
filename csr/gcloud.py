"""Thin wrappers around gcloud subprocess calls."""


def configuration_exists(name: str) -> bool:
    """Check if a gcloud named configuration exists."""
    # Placeholder for Step 2
    raise NotImplementedError


def auth_login(config_name: str) -> None:
    """Run gcloud auth login with the given configuration."""
    # Placeholder for Step 2
    raise NotImplementedError


def scp_to_cloudshell(config_name: str, local_path: str, remote_filename: str) -> None:
    """Upload a file to Cloud Shell via scp."""
    # Placeholder for Step 3
    raise NotImplementedError


def launch_detached(config_name: str, remote_command: str, log_path: str):
    """Launch a detached gcloud cloud-shell ssh process."""
    # Placeholder for Step 3
    raise NotImplementedError
