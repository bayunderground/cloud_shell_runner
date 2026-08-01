"""Login command: register a nickname for a gcloud configuration."""

import sys

from csr import fixtures
from csr import gcloud


def login(nickname: str, gcloud_config_name: str) -> None:
    """Register nickname -> gcloud config mapping.

    Steps:
    1. Check if gcloud config exists
    2. Run interactive auth login
    3. Save nickname -> config mapping
    """
    # 1. Check if configuration exists
    if not gcloud.configuration_exists(gcloud_config_name):
        print(
            f"Error: gcloud configuration '{gcloud_config_name}' does not exist.\n"
            f"Create it first with: gcloud config configurations create {gcloud_config_name}",
            file=sys.stderr,
        )
        sys.exit(1)

    # 2. Run interactive auth login (lets stdio inherit for browser flow)
    try:
        gcloud.auth_login(gcloud_config_name)
    except KeyboardInterrupt:
        print("\nLogin cancelled.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error during login: {e}", file=sys.stderr)
        sys.exit(1)

    # 3. Save nickname -> config mapping
    accounts = fixtures.load_accounts()
    accounts[nickname] = gcloud_config_name
    fixtures.save_accounts(accounts)

    print(f"Successfully registered '{nickname}' -> '{gcloud_config_name}'")
