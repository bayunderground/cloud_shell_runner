# CLAUDE.md — Cloud Shell Runner (`csr`)

## What this is

A local CLI that launches scripts on Cloud Shell in the background and can
stop them on demand, across multiple Google accounts. Three subcommands:
`csr login`, `csr run`, `csr stop`.

This is **not** a VM-management tool and it does **not** provision or tear
down Cloud Shell itself — Cloud Shell auto-starts on connect and
auto-terminates on its own idle schedule regardless of what this tool does.
What this tool manages is the *run* — the background local process and,
where the remote script cooperates, the remote loop it's driving.

See `DEVELOPMENT_PLAN.md` for the staged build order.

## Core mechanism: named configurations, not per-instance keys

Cloud Shell is one per Google account — there's no fleet of instances to
manage and no per-instance SSH key to store. Multi-account support instead
rides on gcloud's own **named configurations**
(`gcloud config configurations create/list/describe`), which already model
"different Google account, different credential set."

`fixtures/accounts.json` exists purely to give those configs a memorable
nickname. It is **not** a credential store and does not duplicate anything
gcloud already tracks:

```json
{
  "work": "work-gcloud-config",
  "personal": "personal-gcloud-config"
}
```

`login` does not create the gcloud configuration — the user is expected to
have already run `gcloud config configurations create <name>`. `login`
only confirms the named config exists (`gcloud config configurations
describe <name>`, which errors cleanly if it doesn't — see verified
mechanics below) and then records the nickname → config-name mapping.

## Verified gcloud mechanics

These were confirmed against current `gcloud` docs during planning (not
assumed from training-data recall, per the handoff's instruction — gcloud
syntax drifts):

- **`--configuration=<name>` is a gcloud-wide flag**, available on every
  command including `cloud-shell ssh` and `cloud-shell scp` — it is not
  something specific to the `cloud-shell` command group. This is the whole
  multi-account mechanism: prefix any `cloud-shell` call with
  `--configuration=<resolved-config-name>` to run it under that account's
  credentials rather than whatever gcloud's currently-active config is.
- **`--authorize-session`** is a flag specific to `cloud-shell ssh`
  (not `scp`) that sends OAuth credentials into the Cloud Shell session so
  Cloud-side `gcloud`/`gsutil` calls work without a separate manual auth
  step. It composes with `--configuration` — they're independent flags on
  the same command.
- **`gcloud cloud-shell ssh --command="..."` starts Cloud Shell if needed
  and runs the command within that one call.** There is no separate "wait
  for boot" step to script around.
- **`gcloud cloud-shell scp` uses `cloudshell:`/`localhost:` path
  prefixes**, not a bare local-path/remote-path pair the way `scp(1)` or
  `gcloud compute scp` work:
  `gcloud cloud-shell scp localhost:~/local_script.sh cloudshell:~/script.sh`.
  This also takes `--configuration`.
- **`gcloud config configurations describe <name>`** is the existence
  check for `login` — errors cleanly (nonzero exit, message on stderr) if
  the named configuration doesn't exist, so `login` can fail fast with a
  clear message rather than silently recording a dead mapping.

## The three commands

### `csr login <nickname> <gcloud-config-name>`

1. `gcloud config configurations describe <gcloud-config-name>` — confirm
   it exists; if not, fail with a clear message (do not create it).
2. `gcloud auth login --configuration=<gcloud-config-name>` — interactive,
   opens a browser. This is the one deliberately interactive step in the
   whole tool.
3. Write/update `nickname → gcloud-config-name` in `fixtures/accounts.json`.

### `csr run <nickname> <script-path> [-- <script-args>...]`

1. Resolve `nickname` → config name via `fixtures/accounts.json`. Unknown
   nickname → clear error pointing at `csr login`.
2. Upload the script:
   `gcloud cloud-shell scp --configuration=<config> localhost:<script-path> cloudshell:~/<script-basename>`
3. Launch, as a **detached, non-blocking local subprocess**:
   `gcloud cloud-shell ssh --configuration=<config> --authorize-session --command="bash ~/<script-basename> <args>"`
   redirecting stdout/stderr to `runs/<nickname>_<timestamp>.log`. `run`
   returns as soon as this subprocess is launched — it does not wait for
   the remote command to finish. `--command` already starts Cloud Shell if
   needed and runs the script within that one call, so there's nothing
   further to orchestrate here.
4. Write the local subprocess's PID to `fixtures/running/<nickname>.pid`
   so `stop` can find it later, possibly from a different terminal.

### `csr stop <nickname>`

1. Resolve `nickname` → config name, same as `run`.
2. Read `fixtures/running/<nickname>.pid`.
   - **No PID file present:** clean no-op — print a message that there's
     no known in-progress run for this nickname, exit 0. This is the
     expected outcome if the run already finished or `stop` is called
     twice; it is not an error.
   - **PID file present:** check whether that PID is a live process. If
     so, send it a termination signal (fast path — killing the local
     `gcloud cloud-shell ssh` process drops the SSH connection, which
     *usually* takes the remote command down with it as a result of the
     dropped connection, though this isn't fully guaranteed — see the
     script-author constraint below).
3. **Regardless of whether step 2 found and killed a live PID**, also
   fire a separate, quick, non-backgrounded call:
   `gcloud cloud-shell ssh --configuration=<config> --command="touch ~/.stop_<nickname>"`
   This is a deliberate second mechanism that always runs, not a
   fallback used only when the PID kill fails.
4. Remove the PID file.

**Constraint this places on remote scripts:** the stop-flag mechanism only
works if the remote script polls for it and exits cleanly on its own —
e.g. `while [ ! -f ~/.stop_<nickname> ]; do work; sleep N; done`. A
single-pass, non-looping remote script has no way to honor the stop-flag;
it can only be interrupted via the PID-kill path dropping its SSH
connection, and even that path isn't fully guaranteed (see the "what we
couldn't verify" list in `DEVELOPMENT_PLAN.md`). **Anyone writing a script
to run through this tool needs to know this** — document it prominently
wherever scripts-for-csr get written up, not just here.

## File layout

```
csr/
  __init__.py
  cli.py            # subcommand parsing/dispatch (csr login|run|stop)
  fixtures.py        # read/write fixtures/accounts.json, PID files
  gcloud.py           # thin wrappers around the gcloud subprocess calls
  commands/
    login.py
    run.py
    stop.py
fixtures/
  accounts.json       # nickname -> gcloud config name (source of truth for nicknames)
  running/
    <nickname>.pid     # one per in-progress run
runs/
  <nickname>_<timestamp>.log   # per-run output, one file per run
```

## Conventions

- **Invocation style:** subcommands (`csr login`, `csr run`, `csr stop`),
  not a single entry point with mode flags.
- **Error handling:** minimal. Let `gcloud`'s own errors surface — don't
  wrap subprocess failures in retry logic. The one deliberate exception is
  the "no PID file" case in `stop`, which is a designed no-op, not an
  error to be retried around.
- **Fixtures format:** flat JSON dict, `{nickname: gcloud-config-name}`.
  No nesting, no metadata beyond the mapping — the file's only job is
  giving configs a memorable name.
- **Output naming:** `runs/<nickname>_<timestamp>.log`, one file per `run`
  invocation.
- Match idiomatic Python CLI conventions generally (argument parsing via
  `argparse` subparsers or an equivalent, `subprocess.Popen` for the
  detached launch, no external framework unless a step in
  `DEVELOPMENT_PLAN.md` calls for one).

## Explicitly out of scope

- Managing GCE VM instances, per-instance SSH keys, or anything at the
  Compute Engine layer. Considered and ruled out during planning — this
  tool only ever talks to Cloud Shell.
- Creating or modifying gcloud named configurations. `csr login`
  references configs the user already created; it never creates one.
- Any shutdown/teardown logic for Cloud Shell as a resource. Cloud Shell
  manages its own lifecycle. `stop` only ever targets the run this tool
  started (the local subprocess and/or the remote script's own loop),
  never Cloud Shell itself.

## How to extend

- New per-run behavior (e.g. a `--tail` flag to stream the log file after
  launch) belongs in `commands/run.py` and should not change the
  detached-launch contract — `run` must keep returning immediately.
- New gcloud-call wrappers go in `gcloud.py` so the `--configuration`
  scoping logic (and any future flag composition) lives in one place
  rather than being repeated per-command.
- If a future need arises to track more than the nickname → config
  mapping in fixtures, extend the JSON shape deliberately and update this
  doc — don't let fixtures quietly become a second credentials store.
