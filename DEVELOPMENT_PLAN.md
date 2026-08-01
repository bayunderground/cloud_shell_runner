# DEVELOPMENT_PLAN.md — Cloud Shell Runner (`csr`)

Staged, verifiable steps. Each step should be independently testable
before moving to the next — this is a plan to work through, not a
monolithic prompt to implement all at once. See `CLAUDE.md` for the
architecture these steps implement.

## What was verified during planning (and how)

Per the handoff's instruction not to guess on gcloud mechanics, the
following were checked against current `gcloud` docs before this plan was
written:

- `--configuration=<name>` is a gcloud-wide flag on every command,
  including `cloud-shell ssh` and `cloud-shell scp` — not something
  specific to the `cloud-shell` group.
- `--authorize-session` is `cloud-shell ssh`-specific and composes cleanly
  with `--configuration` as an independent flag on the same call.
- `cloud-shell ssh --command="..."` starts Cloud Shell if needed and runs
  the command within that single call — no separate boot-wait step.
- `cloud-shell scp` uses `cloudshell:`/`localhost:` path prefixes, not a
  bare local/remote path pair.
- `gcloud config configurations describe <name>` is the clean existence
  check for a named configuration (nonzero exit if absent).

## What could **not** be verified from docs alone (must confirm during Step 2/6)

These need real testing against a live account, not just documentation —
flag them again if reality diverges from the assumption:

- Whether killing the local `gcloud cloud-shell ssh` subprocess reliably
  terminates the corresponding remote command, or whether the remote side
  can survive a dropped connection in some cases (e.g. remote-side
  `nohup`/`disown`). This determines how much weight `stop` can put on the
  PID-kill path versus needing the stop-flag path to do the real work.
  Test explicitly in Step 6.
- Whether Cloud Shell's home-directory persistence reliably holds the
  stop-flag file across separate `ssh` calls for the same account, and
  over what timescale a flag file might get cleaned up after long idle
  gaps between calls.
- Exact `historyTypes`-style edge cases don't apply here (that's the
  Gmail-notifier project) — the equivalent open item for *this* project is
  simply: confirm current `gcloud` version installed in the dev/test
  environment matches what was checked in docs, since `gcloud` does
  change. Run `gcloud version` and `gcloud cloud-shell ssh --help` /
  `gcloud cloud-shell scp --help` at the start of Step 1 as a sanity
  check, not just a one-time doc lookup.

## Confirmed conventions (from clarifying questions)

- Subcommands: `csr login`, `csr run`, `csr stop`.
- Minimal error handling — surface `gcloud`'s own errors as-is, no retry
  wrapping around the subprocess calls.
- Output log naming: `runs/<nickname>_<timestamp>.log`.
- Fixtures format: flat JSON, `{nickname: gcloud-config-name}`.

---

## Step 1 — Project skeleton + fixtures I/O

**Goal:** the file layout exists and fixtures read/write works, no gcloud
calls yet.

- Create the `csr/` package and `fixtures/` directory per the layout in
  `CLAUDE.md`.
- Implement `fixtures.py`:
  - `load_accounts() -> dict[str, str]` — read `fixtures/accounts.json`,
    return `{}` if the file doesn't exist yet (first run).
  - `save_accounts(dict[str, str])` — write it back.
  - `resolve_nickname(nickname: str) -> str` — look up, raise a clear
    exception (with a message pointing at `csr login`) if missing.
  - PID file helpers: `write_pid(nickname, pid)`,
    `read_pid(nickname) -> int | None`, `remove_pid(nickname)`.
- `argparse` subcommand skeleton in `cli.py` with `login`, `run`, `stop`
  wired to stub functions that just print what they'd do.

**Verify:** unit tests (or a quick manual run) for `fixtures.py` covering:
missing file → `{}`, round-trip save/load, unknown-nickname error message.
Run `gcloud version` and confirm `cloud-shell` is available in the
installed SDK, per the note above.

## Step 2 — `csr login`, real gcloud calls

**Goal:** `login` fully works end to end against a real account.

- Implement `gcloud.py`: a thin wrapper, e.g.
  `configuration_exists(name: str) -> bool` (shells out to
  `gcloud config configurations describe <name>`, returns based on exit
  code) and `auth_login(config_name: str)` (shells out to
  `gcloud auth login --configuration=<name>`, interactive, let it inherit
  stdio so the browser flow works normally).
- Implement `commands/login.py` using these: describe → fail clearly if
  absent → `auth_login` → `fixtures.save_accounts(...)`.
- Wire into `cli.py`.

**Verify:** run `csr login <nickname> <a real existing config name>`
against your own account. Confirm:
- It fails clearly (no crash, no traceback) if given a config name that
  doesn't exist.
- On success, `fixtures/accounts.json` has the right mapping.
- Running `login` again with the same nickname but a different config
  name updates the mapping (don't silently duplicate or ignore it).

## Step 3 — `csr run`, upload + detached launch (no stop yet)

**Goal:** `run` uploads a script and launches it in the background,
returns immediately, and a log file fills in over time. `stop` doesn't
exist yet — you'll need to let test runs finish on their own or kill them
manually outside the tool for now.

- Extend `gcloud.py`:
  - `scp_to_cloudshell(config_name, local_path, remote_filename)` —
    shells out to
    `gcloud cloud-shell scp --configuration=<config> localhost:<local_path> cloudshell:~/<remote_filename>`.
  - `launch_detached(config_name, remote_command) -> subprocess.Popen` —
    builds the
    `gcloud cloud-shell ssh --configuration=<config> --authorize-session --command="<remote_command>"`
    call and launches it with `subprocess.Popen`, stdout/stderr redirected
    to the log file, **not** blocking (don't call `.wait()`).
- Implement `commands/run.py`: resolve nickname → scp the script → build
  the remote command string (`bash ~/<script> <args>`) → open the log file
  → `launch_detached` → `fixtures.write_pid(nickname, process.pid)` →
  return immediately.
- Log file naming: `runs/<nickname>_<timestamp>.log`, created at launch
  time even if empty initially.

**Verify:** write a trivial test script (e.g. `echo hello; sleep 30; echo
done`) and run `csr run <nickname> ./test_script.sh`. Confirm:
- `csr run` returns to the terminal in well under a second — it must not
  block for the 30-second sleep.
- `fixtures/running/<nickname>.pid` is written with a real, live PID.
- `runs/<nickname>_<timestamp>.log` starts filling with `hello` shortly
  after launch and `done` roughly 30 seconds later, without you having to
  do anything further.

## Step 4 — `csr stop`, PID-kill path

**Goal:** `stop` can interrupt a `run` in progress via the PID-kill
mechanism, and handles the no-PID-file case as a clean no-op.

- Implement `commands/stop.py`, PID-kill portion only for this step:
  resolve nickname → read PID file → if none, print a clear "no
  in-progress run" message and exit 0 (this is success, not failure) → if
  present, check liveness and send a termination signal if live → remove
  PID file.

**Verify:**
- `csr stop <nickname>` with no prior `run` (or after a run already
  finished) → clean message, exit 0, no traceback.
- Start a long-running test script via `run`, then `csr stop` shortly
  after. Confirm the local `gcloud cloud-shell ssh` process is gone and
  the PID file is removed. **Separately check whether the remote command
  also stopped** (e.g. have the test script write timestamps to a file
  Cloud Shell keeps, and check via a plain `gcloud cloud-shell ssh
  --command="cat ..."` whether it kept writing after the local kill).
  This is the "must verify" item from planning — record what you actually
  observe here, since it determines how much `stop` can lean on this path
  alone versus needing Step 5's stop-flag mechanism to do the real work.

## Step 5 — `csr stop`, stop-flag path

**Goal:** the second, always-fires mechanism is in place, independent of
whether the PID-kill in Step 4 succeeded.

- Extend `commands/stop.py`: after the PID-kill handling (regardless of
  its outcome), fire a separate, non-backgrounded call —
  `gcloud cloud-shell ssh --configuration=<config> --command="touch ~/.stop_<nickname>"`
  — and let it complete before `stop` returns (this one call is fine to
  block on; it's a quick single command, not the long-running job).

**Verify:** write a test script that loops and checks the flag, per the
pattern in `CLAUDE.md`:
```bash
while [ ! -f ~/.stop_<nickname> ]; do echo tick; sleep 5; done
echo "stopped cleanly"
```
Run it via `csr run`, then `csr stop`. Confirm the log shows `stopped
cleanly` shortly after `stop` is called — this confirms the flag file
mechanism works end to end, independent of the PID-kill path. Also
confirm calling `csr stop` a second time right after (flag already set,
PID file already gone) behaves as a clean no-op per Step 4's contract.

## Step 6 — Edge cases from the "must verify" list

**Goal:** the tool behaves reasonably for the scenarios flagged during
planning that couldn't be checked from docs alone.

- **Stale/renamed/deleted gcloud configuration:** manually delete or
  rename a gcloud config that has an entry in `fixtures/accounts.json`,
  then try `csr run` against that nickname. It should fail with a clear
  message pointing at the underlying gcloud error (per "minimal error
  handling" — don't build elaborate detection, just don't let it crash
  uninformatively). Decide here whether `login` should also expose a way
  to re-point an existing nickname at a different config, or whether
  re-running `login` with the same nickname (per Step 2) already covers
  it.
- **PID-kill reliability, revisited:** if Step 4's observation showed the
  remote command sometimes survives the local kill (e.g. via remote-side
  `nohup`), confirm the stop-flag path from Step 5 is sufficient
  compensation for scripts that use the polling loop, and make sure this
  limitation is stated plainly in whatever documentation reaches people
  writing scripts for this tool — not just in this plan.
- **Stop-flag persistence over idle gaps:** if practical, test `run` →
  wait long enough for Cloud Shell to have gone idle once → `run` again on
  the same nickname → confirm the home directory (and thus fixtures like
  old flag files) persisted as expected across the idle gap, per Cloud
  Shell's Persistent-Disk-backed home directory.

## Step 7 — Polish pass

**Goal:** the tool is pleasant to actually use, without adding scope this
project explicitly excludes.

- Review error messages end to end — since error handling is deliberately
  minimal, make sure the *messages that do exist* (unknown nickname,
  missing config, no PID file) are clear rather than raw tracebacks.
- Add a `--help` pass on all three subcommands.
- Confirm the constraint on remote scripts (must poll for the stop-flag to
  honor `stop` cleanly) is documented somewhere a script author would
  actually see it — a `README.md` or a comment template, not just buried
  in `CLAUDE.md`.
- Explicitly confirm nothing in this implementation drifted toward the
  ruled-out designs: no GCE VM handling, no per-instance SSH key storage,
  no code path that tries to start/stop Cloud Shell itself as a resource.
