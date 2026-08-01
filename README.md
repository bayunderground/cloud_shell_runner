# Cloud Shell Runner (`csr`)

A local CLI that launches scripts on Cloud Shell in the background and can stop them on demand, across multiple Google accounts.

## Installation

```bash
# Clone the repository
git clone https://github.com/bayunderground/cloud_shell_runner.git
cd cloud_shell_runner

# Install dependencies (if any)
pip install -r requirements.txt

# Make the CLI available
pip install -e .
```

## Quick Start

```bash
# 1. Register a nickname for your gcloud config
csr login my-account my-gcloud-config

# 2. Run a script on Cloud Shell
csr run my-account ./my_script.sh

# 3. Stop the script
csr stop my-account
```

## Commands

### `csr login <nickname> <gcloud-config-name>`

Register a memorable nickname for an existing gcloud configuration.

```bash
csr login work work-gcloud-config
csr login personal personal-gcloud-config
```

**Note:** This does not create the gcloud configuration. Create it first with:
```bash
gcloud config configurations create <name>
```

### `csr run <nickname> <script-path> [-- <script-args>...]`

Upload a script to Cloud Shell and run it in the background.

```bash
csr run work ./deploy.sh production
csr run personal ./backup.sh daily
```

The command returns immediately - the script runs in the background on Cloud Shell.

Output is logged to `runs/<nickname>_<timestamp>.log`.

### `csr stop <nickname>`

Stop a running script on Cloud Shell.

```bash
csr stop work
```

This uses two mechanisms:
1. **PID-kill**: Terminates the local gcloud process
2. **Stop-flag**: Creates `~/.stop_<nickname>` on Cloud Shell

## ⚠️ Important: Stop-Flag Mechanism

**For script authors:** The stop mechanism only works if your script polls for the stop flag and exits cleanly on its own.

Your script **must** include a polling loop like this:

```bash
#!/bin/bash
NICKNAME="my-script"  # Must match the nickname used with csr run

while [ ! -f ~/.stop_${NICKNAME} ]; do
    # Your work here
    echo "Working..."
    sleep 5
done

echo "Stopped cleanly"
```

**Without this polling loop:**
- The PID-kill path may not reliably terminate the remote command
- The script will continue running until Cloud Shell's idle timeout

**With this polling loop:**
- `csr stop` creates `~/.stop_<nickname>`
- Your script detects the flag and exits cleanly
- This is the reliable way to stop remote scripts

## File Structure

```
cloud_shell_runner/
├── csr/
│   ├── __init__.py
│   ├── cli.py            # CLI entry point
│   ├── fixtures.py       # Read/write fixtures
│   ├── gcloud.py         # gcloud subprocess wrappers
│   └── commands/
│       ├── login.py
│       ├── run.py
│       └── stop.py
├── fixtures/
│   ├── accounts.json     # Nickname -> gcloud config mapping
│   └── running/          # PID files for active runs
├── runs/                 # Log files from runs
├── examples/
│   └── test_polling.sh   # Example polling script
└── README.md
```

## Conventions

- **Subcommands**: `csr login`, `csr run`, `csr stop`
- **Error handling**: Minimal - gcloud's own errors surface naturally
- **Log files**: `runs/<nickname>_<timestamp>.log`
- **Fixtures**: Flat JSON, `{nickname: gcloud-config-name}`

## What This Tool Does NOT Do

- Manage GCE VM instances or SSH keys
- Create or modify gcloud named configurations
- Start or stop Cloud Shell itself (it manages its own lifecycle)

## License

See LICENSE file for details.
