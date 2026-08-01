"""CLI entry point for csr."""

import argparse
import sys

from csr.commands import login, run, stop


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="csr",
        description="Launch scripts on Cloud Shell in the background and stop them on demand.",
    )
    subparsers = parser.add_subparsers(dest="command")

    # login subcommand
    login_parser = subparsers.add_parser("login", help="Register a nickname for a gcloud config")
    login_parser.add_argument("nickname", help="Memorable name for this account")
    login_parser.add_argument("gcloud_config_name", help="gcloud configuration name")

    # run subcommand
    run_parser = subparsers.add_parser("run", help="Upload and run a script on Cloud Shell")
    run_parser.add_argument("nickname", help="Account nickname (from csr login)")
    run_parser.add_argument("script_path", help="Local script to upload and run")
    run_parser.add_argument("script_args", nargs="*", help="Arguments to pass to the script")

    # stop subcommand
    stop_parser = subparsers.add_parser("stop", help="Stop a running script")
    stop_parser.add_argument("nickname", help="Account nickname to stop")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "login":
        login.login(args.nickname, args.gcloud_config_name)
    elif args.command == "run":
        run.run(args.nickname, args.script_path, args.script_args)
    elif args.command == "stop":
        stop.stop(args.nickname)


if __name__ == "__main__":
    main()
