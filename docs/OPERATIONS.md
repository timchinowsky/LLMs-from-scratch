# Operations — synthetic development release

## Data and faults

State is under `state/` unless configured otherwise; the directory is mode 0700 and
credentials are mode 0600. The CLI sets umask 077. Keep this directory out of Git and
backups intended for sharing. Ordinary logs omit transcript content and access tokens;
HTTP access logging is disabled. The development server writes lifecycle/error logs
to its terminal, not a persistent unbounded file. Rotated operational logging is pending.

Below min_free_mb, final writes are rejected and status reports a fault. SQLite errors
also latch a visible fault until the cause is repaired and the app restarts. There is
no automatic transcript deletion. Monitor history/database/event growth and free disk.
Export is available from the authenticated dashboard as streaming NDJSON.

## Consistent backup and isolated restore

Tested backup command, from the repository root after at least one server startup:

```sh
.venv/bin/parents-companion backup --output /tmp/parents-backup.sqlite3
```

Choose a new private destination each time; existing paths are rejected. The command
uses SQLite's backup API, including committed WAL data. It changes the destination
instance UUID, so clients of a restored database must resynchronize. It does not
include role credentials or machine configuration. Back those up separately using
protected storage. Never copy a running main SQLite file without its WAL handling.

Tested isolated restore procedure (use a fresh directory; do not overwrite production):

```sh
mkdir -m 700 /tmp/parents-restored
cp /tmp/parents-backup.sqlite3 /tmp/parents-restored/companion.sqlite3
printf 'data_dir = "/tmp/parents-restored"\n' > /tmp/parents-restored.toml
.venv/bin/parents-companion --config /tmp/parents-restored.toml serve
```

Stop any server on port 8765 first. New role tokens are generated for a fresh restore.
Verify count, search, timestamps, acknowledgement and mute before using restored data.
Automated backup tests use isolated temp files and assert integrity and instance changes.

## Recovery, updates and rollback

Stop with Ctrl-C or SIGTERM; start with the README command. Sessions expire at restart,
while finals, events, role tokens, and local mute survive. Provisional text is discarded.
After fixing low disk or permissions, restart and verify status plus a synthetic write.
Do not infer microphone health from the status: no microphone is implemented.

To rotate tokens, stop the app, privately remove only credentials.json, and restart.
Previously issued sessions die with the stopped process. Keep tokens out of shell logs.

Before updating, stop the server, back up data/configuration/credentials and record
`git rev-parse HEAD`. Review source changes, install with the frozen lock, run tests,
and restart. Future schema migrations require explicit backup/compatibility tests.
Version 0.1 supports schema 1 only and refuses newer schemas. Rolling back to the old
LLM repository is not an application rollback. There is no older app release yet, so
previous-release rollback testing is pending. A source checkout of this milestone plus
its matching protected backup is the initial recovery checkpoint.

No service or system audio changes have been installed. Uninstall by stopping the
process and removing its virtual environment; preserve state and backups unless the
operator explicitly requests deletion. Reboot/session supervision is pending Stage 7.
