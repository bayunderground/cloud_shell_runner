"""Read/write fixtures: accounts.json and PID files."""

import json
import os

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fixtures")
ACCOUNTS_FILE = os.path.join(FIXTURES_DIR, "accounts.json")
RUNNING_DIR = os.path.join(FIXTURES_DIR, "running")


class NicknameNotFoundError(Exception):
    """Raised when a nickname is not found in accounts.json."""


def load_accounts() -> dict[str, str]:
    """Read fixtures/accounts.json, return {} if file doesn't exist."""
    if not os.path.exists(ACCOUNTS_FILE):
        return {}
    with open(ACCOUNTS_FILE, "r") as f:
        return json.load(f)


def save_accounts(accounts: dict[str, str]) -> None:
    """Write accounts dict back to fixtures/accounts.json."""
    os.makedirs(FIXTURES_DIR, exist_ok=True)
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, indent=2)


def resolve_nickname(nickname: str) -> str:
    """Look up nickname in accounts.json. Raise NicknameNotFoundError if missing."""
    accounts = load_accounts()
    if nickname not in accounts:
        raise NicknameNotFoundError(
            f"Unknown nickname '{nickname}'. Run 'csr login' first."
        )
    return accounts[nickname]


def write_pid(nickname: str, pid: int) -> None:
    """Write PID to fixtures/running/<nickname>.pid."""
    os.makedirs(RUNNING_DIR, exist_ok=True)
    pid_file = os.path.join(RUNNING_DIR, f"{nickname}.pid")
    with open(pid_file, "w") as f:
        f.write(str(pid))


def read_pid(nickname: str) -> int | None:
    """Read PID from fixtures/running/<nickname>.pid, return None if missing."""
    pid_file = os.path.join(RUNNING_DIR, f"{nickname}.pid")
    if not os.path.exists(pid_file):
        return None
    with open(pid_file, "r") as f:
        return int(f.read().strip())


def remove_pid(nickname: str) -> None:
    """Remove PID file if it exists."""
    pid_file = os.path.join(RUNNING_DIR, f"{nickname}.pid")
    if os.path.exists(pid_file):
        os.remove(pid_file)
