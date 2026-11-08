# Parents Companion: Codex development and testing instructions

Version: 1.0 · Prepared November 8, 2026

## How to use this document

Place this file in the root of a dedicated Git repository as `DEVELOPMENT_PLAN.md`. Start Codex in that repository on the target Linux laptop, or on a development Linux machine with access to representative audio hardware.

Give Codex this instruction:

> Read DEVELOPMENT_PLAN.md. Inspect the repository and host, then implement the next unfinished stage. Create and maintain AGENTS.md, STATUS.md, and the test reports specified in the plan. Implement and run the software; do not stop at a proposal. Proceed through stages whose prerequisites are available. Record hardware-dependent checks as pending when you cannot perform them, and continue independent work. Never report simulated tests as proof that the real microphone, speakers, network, or desktop work. Make a Git commit after each verified milestone. Finish each session with exact commands to run, the current test results, and the next unfinished task.

This document is an implementation specification. Its acceptance criteria are proposed targets, not claims that software already exists or tests have passed.

## 1. Product goal and scope

Build a companion application for elderly parents on a Linux laptop. It continuously listens through a microphone while listening is enabled, transcribes detected speech, and saves the transcript. A caregiver reads the transcript remotely and manually operates the laptop, including playing videos and displaying messages.

The caregiver uses a browser on a phone or computer connected through Wi-Fi and the internet. The two devices may be on different networks. The parents' laptop is the authoritative server and media playback device.

Required behavior:

- Listening and recording continue independently of the visible browser or media player.
- Save all finalized detected-speech transcripts, not just text classified as requests. Speech detection will not reliably distinguish a parent from a television or visitor; do not claim otherwise.
- Show live text, persistent history, and clear connection and microphone status to the caregiver.
- Let the caregiver play supported media, pause, resume, stop, seek, adjust volume, and display a large message.
- Play media on the parents' actual screen and speakers. Send commands and URLs across the control connection; the laptop obtains the media itself.
- Provide a simple local view with large text, microphone status, a listening/mute control, and a stop-playback control.
- Respect a locally selected mute until it is explicitly cleared locally. A remote caregiver must not silently override local mute.
- Recover from ordinary process crashes, network interruptions, and microphone disconnection.
- Preserve working versions and reproducible setup instructions in Git.

Keep the first release focused. Do not add autonomous interpretation or execution of spoken requests, speaker identification, a conversational persona, a mobile native app, or public internet hosting. ChatGPT Dot is optional for development coordination; it is not a runtime dependency. The deployed app must operate without Codex or ChatGPT running.

## 2. Architecture and initial technology choices

Use one repository and a small set of local processes. Do not introduce Kubernetes, a message broker, a distributed database, or microservices without a demonstrated requirement.

| Component | Initial choice | Responsibility |
| --- | --- | --- |
| Audio | PipeWire; capture adapter selected after host inspection | Select microphone, acquire audio, provide playback reference for echo cancellation |
| Segmentation | Silero VAD or a justified equivalent | Detect speech boundaries with pre-roll and generous pauses |
| Transcription | Replaceable Python adapter; begin with local faster-whisper when practical | Produce final text and optional partial text |
| Optional cloud transcription | OpenAI transcription API | Alternative selected explicitly in configuration |
| Persistence | SQLite with migrations and transactions | Transcript history, durable event sequence, command records, settings |
| Backend | Python + FastAPI | HTTP API, WebSocket updates, authorization, command routing |
| Frontend | Simple responsive HTML/CSS/JavaScript | Caregiver dashboard and local display |
| Media | mpv controlled through a local Unix-domain socket | Playback and observed player state |
| Connectivity | Tailscale and Tailscale Serve | Private HTTPS access from authorized caregiver devices |
| Supervision | systemd user services | Start and restart application processes in the desktop session |
| General remote operation | Separately configured remote desktop, such as RustDesk | Arbitrary browser interaction and maintenance |

The backend should remain responsive if transcription is slow or crashes. Run transcription outside the HTTP event loop, preferably in a worker process. Audio capture must not block waiting for a database write, network request, or model inference. Use bounded queues and report overflow rather than growing memory without limit.

The database is owned by the backend or a clearly defined persistence component. Keep write ownership simple. Implement enough process separation to isolate failures, without creating unnecessary network services on the laptop.

The remote desktop program is separate from the app. It must share the parents' existing desktop, not create a different invisible desktop session.

## 3. Rules for Codex execution and continuity

### At the beginning of every session

1. Read this plan, `AGENTS.md`, `STATUS.md`, and relevant test reports.
2. Inspect `git status`, the current branch, and recent commits. Preserve unrelated user changes.
3. Determine whether this is the actual target laptop, a development host, or a cloud environment.
4. Identify the next stage and the smallest useful implementation increment.
5. State any material assumption. Ask only for a missing decision that blocks useful work.

### During implementation

- Implement and test working behavior, not just scaffolding, screenshots, or mock demonstrations.
- Prefer existing maintained components for audio, transcription, and playback.
- Verify current primary documentation before using version-sensitive SDK methods, model names, configuration syntax, or installation commands. Pin the versions that were actually tested.
- Do not silently switch local speech recognition to a cloud provider. Show the selected backend and whether audio leaves the laptop.
- Keep API keys in a protected local configuration or credential mechanism. Never embed them in frontend code, print them in logs, or commit them.
- Avoid copying private transcript or audio contents into coding prompts, test reports, or Git. Use synthetic fixtures for repeatable tests; use real samples only when supplied for that purpose.
- Do not automatically install updates, reboot, suspend the machine, change login behavior, or change system-wide audio routing while someone is using the laptop. Prepare changes and apply them in a maintenance window agreed with the operator. Ordinary project edits and automated tests should proceed without repeated confirmation.
- When hardware, credentials, or a second network are unavailable, record the exact blocked test and continue work that does not depend on it.

### At each milestone

- Run the focused checks relevant to the change, then the required regression suite.
- Fix failures before marking the stage passed.
- Update `STATUS.md` and the stage report with evidence, limitations, and reproduction commands.
- Review the diff for secrets, unintended files, and unrelated changes.
- Commit the verified milestone locally. Never invent Git author details. If identity is missing, preserve the work and report the exact setup needed.
- Push when an authorized remote is configured and pushing is permitted. Never force-push, create a public repository, or publish recordings/transcripts.
- For an incomplete stage, commit a clearly labeled work checkpoint when useful; do not label it verified.

### Required project documents

| File | Contents |
| --- | --- |
| `AGENTS.md` | Concise project rules, architecture boundaries, commands, verification requirements |
| `STATUS.md` | Stage states, current branch/commit, outstanding issues, pending hardware tests, exact next action |
| `README.md` | Install, configure, start, use, and stop the app |
| `docs/ARCHITECTURE.md` | Processes, data flow, API, authentication, failure behavior |
| `docs/OPERATIONS.md` | Recovery, backup/restore, updates, rollback, troubleshooting |
| `docs/HARDWARE_TESTS.md` | Repeatable microphone, speaker, desktop, and real-network procedures |
| `docs/test-reports/stage-NN.md` | Environment, commands, results, measurements, failures, pending checks |
| `config.example.toml` | Documented settings without credentials |

Use stage states `not_started`, `in_progress`, `software_verified_hardware_pending`, `passed`, and `blocked`. A later independent stage may proceed while a hardware gate is pending. Release readiness requires the real hardware gates.

## 4. Data, protocol, and recovery contract

### Transcripts and events

Assign each audio segment a stable ID before transcription. Store its capture start/end timestamps in UTC and its processing state. Display times in the configured local timezone, initially `America/Los_Angeles`. Use a monotonic clock for elapsed-time measurements so a clock correction cannot create negative latency.

A finalized transcript record includes:

- Segment ID and transcript revision, if corrections are supported.
- Capture start/end timestamps and finalization timestamp.
- Text, selected transcription backend/model, and final/error state.
- Capture-session ID and microphone identifier.
- Whether laptop media was playing, when known. This is context, not proof of who spoke.
- Optional caregiver status: unread, acknowledged, handled.

Partial text is visibly provisional. Persist only committed final text as the authoritative transcript. Do not invent confidence percentages when a backend does not provide calibrated confidence information. Do not infer speaker identity.

Write the transcript change and its durable event in the same database transaction, then notify clients. Give durable events a monotonically increasing sequence number. Clients reconnect using the last processed sequence. Replayed events must not produce duplicate transcript rows in the UI.

Use a database-instance identifier in addition to the sequence. After restoring an older backup or rebuilding the database, force a fresh snapshot so an old client cursor cannot silently skip data. If event retention has removed the requested sequence, return an explicit resynchronization response and reload a consistent snapshot.

Paginate history and event replay. Avoid a race between loading history and subscribing: define a snapshot cursor and replay events after that cursor. A final transcript arriving during reconnection must appear exactly once in the rendered history, although transport delivery may be repeated.

### Suggested API

These are application-owned routes, not external provider API claims. Final naming may change if documented.

| Route | Behavior |
| --- | --- |
| `GET /api/status` | Microphone, listening state, worker health, backlog, disk state, player state, version |
| `GET /api/transcripts` | Paginated history/search with stable ordering |
| `PATCH /api/transcripts/{id}` | Caregiver acknowledgement/handled status |
| `GET /api/events?after=...` | Durable event catch-up, with instance ID and resync handling |
| `WS /api/live` | Live events, heartbeat, optional command messages |
| `POST /api/commands` | Validate and durably accept an authorized control command |
| `GET /api/commands/{id}` | Retrieve outcome after an acknowledgement is lost |

Use one command-processing implementation whether submission occurs by HTTP or WebSocket. Choose one primary transport for the first release; do not build redundant transports unnecessarily.

### Commands and actual state

Every command includes a client-generated unique ID, typed action, validated arguments, and a short expiry. Use server receipt time and a bounded validity window; account for clock skew rather than trusting an arbitrary client timestamp. Reject a client replaying an expired command as a new one.

Store command ID, arguments hash, authenticated actor, acceptance time, expiry, state, and result. Reject reuse of an ID with different arguments. Return existing status for a duplicate with identical arguments.

Distinguish `accepted`, `executing`, `succeeded`, `failed`, `expired`, and `unknown`. An acknowledgement of receipt is not proof that the player changed state. Confirm completion from observed player state or an explicit result.

Prefer desired-state commands (`set_paused: true`, `set_volume: 35`) to toggles. Serialize media mutations or apply an explicit state version so two caregiver tabs cannot unpredictably reorder commands. Handle stop commands promptly.

Do not promise exactly-once side effects across a process crash. If the app crashes after a media command executes but before its result is saved, reconcile observed state; if the outcome remains uncertain, report `unknown` and avoid blind replay of non-idempotent commands such as relative seek.

The browser must not queue playback commands while disconnected. After reconnecting, show current state before accepting new controls. Stale commands must not start playback minutes later.

### Network access and credentials

- Bind the backend to loopback by default and expose it privately through Tailscale Serve. Do not open router ports or enable public Funnel hosting.
- Restrict network access to the caregiver identity/devices with the applicable Tailscale policy.
- Authenticate and authorize both HTTP and WebSocket connections. If using Serve identity headers, trust them only through the protected proxy path and explicitly handle local access separately; verify the current documented trust model.
- Establish an authorized browser session, validate WebSocket Origin, and protect state-changing HTTP routes against cross-site requests. Deny unapproved origins; do not use wildcard CORS with credentials.
- Separate local parent controls from remote caregiver privileges. Remote unmute must not clear a local mute lock.
- Keep mpv's IPC socket local and user-restricted. Never expose it directly to the network.
- Use typed commands and argument arrays, never shell interpolation of a URL, transcript, or message.
- Render transcript and message text as text, not HTML. Restrict playback to supported media schemes and configured local media roots; reject arbitrary filesystem access and dangerous URL protocols. Define whether private-network media sources are allowed and enforce that policy.

## 5. Audio and storage behavior

Start with configurable defaults: 0.5 seconds pre-roll, approximately 1.2 seconds end-of-speech silence, and a maximum segment duration around 25 seconds. Tune against actual speech. Split long speech at safe boundaries with overlap/deduplication where needed; do not simply discard the remainder or cut words arbitrarily.

When muted, stop forwarding audio for transcription and clear uncommitted audio buffers. Discard late in-flight results from audio that the user intended to cancel. Already finalized history remains unless explicitly deleted. Preserve local mute across app restart.

Default to local transcription if the hardware meets the measured latency target. If it does not, report the benchmark and implement the explicitly selected cloud option. Keep both behind the same interface; do not require both installed for the app to run.

Cloud outage behavior must be explicit:

- Default: no persistent raw-audio spool. Use a bounded memory queue and show the outage/backlog. If audio cannot be processed before the configured limit, record a visible gap event.
- Optional: a local fallback model, configured and tested in advance.
- Optional: disk spooling, off by default, with a stated retention limit and storage quota. If enabled, replay with original capture timestamps and segment IDs, mark delayed results, and prevent duplicate history.

Temporary audio, logs, queues, and database growth need limits. Retain finalized transcripts until explicit deletion in the first release; do not silently expire them. Provide export, disk-usage reporting, and a documented retention setting for later use. Before storage is exhausted, show a persistent recording fault and stop claiming transcripts are being saved. Never silently delete history to keep the UI green.

Keep audio diagnostics and saved audio samples off by default. Limit ordinary diagnostic logs, omit transcript text and secrets, and rotate them. Proposed default: 14 days and 100 MB, whichever is reached first. Keep synthetic fixtures separate from private operational data.

## 6. Staged implementation and acceptance tests

### Stage 0 — Host inspection and reproducible foundation

**Build**

- Inspect OS, desktop/session type, CPU/RAM/GPU, Python, PipeWire, audio devices, storage, and existing repository state.
- Record the actual environment and whether GUI/audio hardware is available.
- Establish Python packaging, a pinned dependency/lock workflow, formatter/linter, pytest, and a documented development command.
- Create configuration validation, structured logs, temporary test data directories, and `.gitignore` rules for secrets, databases, recordings, caches, and generated operational files.
- Create the required project documents. Reserve a synthetic-data mode that never opens a microphone or calls a paid API.

**Verify**

- A clean environment can install the project and run its smoke tests.
- Invalid configuration produces a useful error without printing secrets.
- Synthetic mode runs without audio hardware, internet, API credentials, or a GUI.
- Record the exact install/run/test commands and make the foundation commit.

### Stage 1 — Persistent transcript pipeline and local UI

**Build**

- SQLite schema/migrations, segment IDs, durable event log, and the transcript API.
- Fake transcription producer with controllable timing, failures, and out-of-order completion.
- Responsive caregiver history/live view, search, acknowledgement, and distinct partial/final text.
- Basic local parent view with a clear synthetic-mode banner during development.

**Verify automatically**

- Final transcripts survive backend restart; partial text cannot masquerade as finalized history.
- Repeated or out-of-order results do not duplicate or misorder history by capture time.
- Reconnect during new-event arrival causes no missing or duplicate displayed entries.
- Pagination boundaries, empty search, Unicode, long text, DST display, and malicious HTML text work correctly.
- Migration from the previous schema preserves records; include a migration fixture once a second schema exists.
- UI works at a phone-width viewport and with keyboard navigation.

**Gate:** Demonstrate synthetic speech becoming saved, searchable transcript entries through the real backend and browser.

### Stage 2 — Real microphone and local transcription

**Build**

- Enumerate/select the microphone by a stable identity where possible, not a fragile numeric index.
- Add a level meter, speech detection, pre-roll, segmentation, bounded queues, and isolated transcription worker.
- Implement faster-whisper adapter and benchmark an appropriate small English model first. Download model assets during setup, not unexpectedly during normal use.
- Implement persistent local mute, disconnection detection, and explicit microphone reselection/recovery. Do not silently switch to another input after losing the selected device.

**Verify automatically**

- Known speech fixtures produce usable text; score normalized word error rate on labeled samples rather than exact punctuation matches.
- Silence and representative non-speech fixtures do not create repeated fabricated sentences.
- Speech start, long pauses, long utterances, overlap boundaries, worker failure, and queue overflow have defined outcomes.
- Muting clears pending audio and prevents late results from a canceled capture generation from appearing.

**Verify on the laptop**

- Speak at the intended distance and volume, including quiet speech and slow phrasing.
- Unplug/replug the selected microphone and test a changed device enumeration.
- Play music and ordinary room noise; record recognition errors and false transcripts.
- Run a 30-minute continuous session and measure CPU, RAM, backlog, and latency.

**Gate:** Reliable microphone capture and persisted text on the real laptop. If local inference cannot keep up, document measurements and proceed to Stage 3; do not hide dropped speech.

### Stage 3 — Optional OpenAI transcription backend

Implement this stage if cloud transcription is selected or needed after Stage 2 benchmarks. Otherwise mark it deferred with the reason; it is not mandatory for a local-only release.

**Build**

- Consult current official OpenAI transcription documentation. Record the tested API/model/version and input format; do not copy stale model names from older examples.
- Keep credentials in the backend. Implement incremental/final results, session renewal where required, reconnect, timeout, rate-limit handling, and bounded retries with backoff/jitter.
- Map provider item IDs to local segment IDs. Preserve capture timestamps and handle out-of-order final results.
- Show cloud audio transmission, backend selection, failure state, and delayed results in the UI.
- Document usage accounting and an estimated monthly cost from measured submitted audio and current pricing. Do not assume silence is free.

**Verify**

- Contract tests with a fake provider cover timeout, invalid credentials, throttling, dropped connections, duplicate events, and renewal boundaries.
- A short explicitly enabled live API smoke test transcribes synthetic or approved audio.
- Credentials never appear in frontend bundles, logs, reports, or Git.
- Disconnect internet during speech. Confirm the configured queue/fallback/gap behavior and recovery without duplicate final records.

**Gate:** Measured live-provider success plus tested failure behavior. Mock success alone is insufficient to mark this stage passed.

### Stage 4 — Private remote dashboard over Wi-Fi and internet

**Build**

- Configure Tailscale/Serve access and application authorization as described above.
- Add event catch-up, heartbeat, connection status, and reconnect backoff.
- Keep the local pipeline running when all browsers disconnect.
- Ensure the dashboard loads without third-party CDN dependencies.

**Verify automatically**

- Unauthorized HTTP, WebSocket, and state-changing requests are rejected.
- Forged identity headers through an untrusted path, invalid origins, CSRF attempts, and malformed payloads fail.
- Lost connections, duplicate events, expired event cursors, and restored databases trigger correct replay or resync.
- A slow browser cannot block capture, persistence, or other clients.

**Verify on real networks**

- Access from a phone on cellular data while the laptop uses home Wi-Fi; this proves the devices are not relying on the same LAN.
- Turn phone Wi-Fi on/off, background and reopen the browser, and change networks.
- Disable the private connection and confirm the dashboard is inaccessible from an unauthorized device.
- Confirm microphone transcription continues with no dashboard open and after a temporary network outage.

**Gate:** Live and historical transcripts are readable from a separately networked authorized device; reconnect catches up correctly.

### Stage 5 — Remote playback and local messages

**Build**

- mpv lifecycle and restricted IPC integration in the parents' active desktop session.
- Typed commands: play supported URL/file, set paused, stop, absolute seek, set volume, display/clear message.
- Durable command IDs, expiry, deduplication, serialization, and outcome reconciliation.
- Observe player state and present it in the dashboard. Preserve a useful parent screen after playback ends or fails.
- Set a conservative configurable maximum volume. Do not change unrelated system audio settings unexpectedly.
- Keep local mute and stop controls accessible while video is fullscreen; support a simple physical button/key binding where available.

**Verify automatically**

- Command receipt, execution, failure, expiry, duplicate IDs, changed arguments, and reconnect queries.
- Crash between sending a command and saving its result yields reconciliation or `unknown`, not an unsupported success claim.
- Malicious URLs, shell syntax, path traversal, HTML messages, and unsupported protocols are rejected or rendered safely.
- Competing browser tabs produce deterministic command order and shared observed state.

**Verify on the laptop**

- Play a local fixture and at least one supported online source; confirm physical screen and speaker output.
- Test pause/resume/seek/stop/volume, offline media failure, and player crash/relaunch.
- Send controls from a phone on another network. Disconnect just after sending a command, then reconnect and inspect its outcome.
- Confirm expired commands do not play later. Test parent stop and mute controls during fullscreen playback.
- Document supported media types and browser-only/DRM services. Do not promise that all websites work in mpv; use remote desktop for unsupported services.

**Gate:** Actual playback is controllable and observed reliably from the remote dashboard.

### Stage 6 — Echo cancellation and speech during playback

**Build**

- Route laptop playback through the configured PipeWire echo-cancellation reference and capture from its cleaned source.
- Include mpv and any browser used for playback in the routing plan.
- Validate the graph after restart/device changes and expose a diagnostic when the intended reference or source is missing.
- Preserve speech capture during playback. Do not mute capture whenever media plays.
- Avoid competing hardware/software echo cancellers unless tested. Document microphone/speaker placement.

**Verify**

- Compare raw and processed capture using short, operator-enabled diagnostic samples.
- Test speech alone, laptop playback alone, and simultaneous speech plus playback.
- Repeat at normal and loud listening levels and the actual seating distance.
- Test slow and quiet phrases such as “please stop that video,” “turn it down,” and “could you play something else.” These remain transcript entries; they must not execute automatically.
- Include a separate room television as an adverse case. Document that laptop-reference echo cancellation does not inherently cancel that source.
- Confirm the beginning and end of the parent's speech are preserved and browser playback is also referenced.

**Gate:** Complete the speech/playback acceptance matrix below. If it fails, adjust microphone placement, playback level, or audio hardware before claiming readiness.

### Stage 7 — Startup, recovery, and storage operations

**Build**

- systemd user-service installation, startup dependencies, health checks, bounded restart backoff, and useful diagnostic commands.
- Launch GUI/audio components in the actual user's graphical session. Do not run the entire application as root. A lingering user service alone does not guarantee a working desktop/audio session.
- Document the login requirement. If unattended reboot recovery needs auto-login, explain that configuration and have the operator choose it during setup.
- Preserve selected devices, local mute, backend configuration, and transcripts across restart. Default to no surprise media autoplay on reboot.
- Add storage warnings, log rotation, transcript export, consistent SQLite backup, restore, and migration rollback procedures.
- Back up SQLite using its supported backup mechanism or a stopped/quiesced database, including required WAL handling; do not copy a live database file naively.
- On suspend/resume, report capture gaps and recover. Do not promise recording while suspended.

**Verify**

- Kill the worker, backend, and player independently; observe correct fault state and recovery.
- Reboot, log out/in, suspend/resume, remove the microphone, disable Wi-Fi, and restore each dependency.
- Simulate low disk, permission errors, and database write failure using test resources, not by filling the real disk.
- Confirm no “recording normally” state appears while persistence is failing.
- Restore a backup into a temporary directory and verify records, client resync, configuration, and startup.
- Test the previous release rollback with compatible data or the corresponding backup. Document schema compatibility limits.

**Gate:** Recovery works on the target laptop and the operator can restore a known working version.

### Stage 8 — Qualification and deployment handoff

**Build/finish**

- Finish accessibility: large readable type, sufficient contrast, keyboard focus, plain-language labels, and status conveyed by text as well as color.
- Complete install/update/uninstall, private-network setup, microphone setup, diagnostics, backup/restore, and remote-desktop instructions.
- Create a tagged release with a reproducible dependency set and known limitations. Include no operational data or credentials.

**Verify**

- Run all required automated tests and inspect the browser at phone and laptop sizes.
- Run at least 8 hours on the target laptop, then a 24-hour qualification run before leaving it unattended in normal service.
- Include playback, speech, quiet periods, remote disconnects, and at least one controlled recovery event.
- Test installation from the tagged version in a clean environment; test actual hardware separately.
- Complete the acceptance matrix and list any unresolved failures. Do not declare release-ready with unverified microphone, echo-cancellation, cross-network, or reboot behavior.

**Gate:** All mandatory gates pass, the caregiver has run the basic controls, and documented recovery/rollback works.

## 7. Acceptance matrix and measurement method

These are initial engineering targets. Measure them on the actual system. If a target is unrealistic, report the result and proposed adjustment; do not quietly weaken the test.

| Area | Initial acceptance target | Evidence |
| --- | --- | --- |
| Recognition, quiet room | At least 18 of 20 representative requests preserve the meaning needed by the caregiver | Labeled private test sheet; report aggregate results |
| Recognition during playback | At least 18 of the same 20 requests remain understandable at intended seating distance and volume | Record placement, volume, and backend |
| Final transcription latency | 95th percentile at or below 5 seconds after actual speech end, including endpoint detection | At least 30 timed utterances; report median/p95/max |
| Dashboard propagation | 95th percentile within 1 second of durable commit under normal connectivity | At least 30 events; define clock synchronization or single-clock measurement |
| Command response | Server acceptance within 1 second and local player's state change within 2 seconds under normal connectivity | At least 30 controls; measure media download/startup separately |
| Media startup | Report actual distribution for tested local and online media | Do not hide buffering behind command acknowledgement |
| Connection status | Mark disconnected/stale within 15 seconds of lost contact | Drop connection and timestamp detection |
| Recovery | Resume connection within 30 seconds after service/network availability returns | Timed restart/network tests, excluding OS boot duration |
| Transcript integrity | No lost committed records or duplicate displayed records in restart/replay tests | Segment IDs, DB assertions, browser checks |
| Silence/noise | No fabricated finalized transcript in a controlled 10-minute silence/non-speech test | Save result count; investigate any failure |
| Playback leakage | No sustained stream of laptop video dialogue in a 10-minute playback-only test | Count leakage events and describe any residual errors |
| Mute | No new post-mute audio is transcribed; local mute survives restart | Capture-generation and hardware tests |
| Long-run resources | No unbounded queue/memory growth and no unexplained capture gaps | 8-hour and 24-hour metrics; measured resource budget |
| Private access | Unauthorized devices/users cannot read history or control playback | HTTP/WS authorization and real-device checks |
| Backup recovery | Restored history is usable and clients correctly resync | Isolated restore report |

Do not score transcription solely by word error rate. A wrong word such as “stop” becoming “start” can matter more than punctuation or article errors. Evaluate preservation of request meaning while keeping the saved transcript faithful to the recognizer output.

A microphone level of zero is not sufficient proof that capture is broken; a quiet room can be silent. Health checks must also track capture callbacks, device presence, worker state, queue age, and successful persistence. Likewise, an open WebSocket is not proof that speech is being processed.

## 8. Required test layers

1. **Unit tests:** segmentation, configuration, command validation, cursor handling, expiry, text escaping, and backend adapters.
2. **Integration tests:** real SQLite transactions/migrations, backend lifecycle, fake audio/provider/player, and process failure recovery.
3. **Browser tests:** live text, history, reconnect, stale state, controls, keyboard access, phone layout, and authorization boundaries.
4. **Opt-in live tests:** a real transcription provider or online media source, with bounded test duration and explicit credentials.
5. **Hardware acceptance:** actual microphone, speakers, echo cancellation, screen, physical controls, and reboot.
6. **Cross-network acceptance:** caregiver device on cellular or another internet connection, including network changes and reconnection.

Normal automated tests must not require private audio, a paid API, internet access, the production database, or an actual audio device. Use temporary state and controllable clocks instead of long sleeps. Keep browser and process integration tests focused on user-visible behavior and meaningful failure modes.

## 9. Configuration and operational deliverables

Document every setting's default, units, allowed values, and whether restart is required. At minimum include:

- Selected microphone and output device; sample format/rate and channel conversion.
- VAD thresholds, pre-roll, silence timeout, maximum segment length.
- Transcription backend/model, language, resource limits, and credential lookup.
- Queue limits, timeout/retry policy, optional spool/fallback policy.
- Data/log paths, storage warning thresholds, log limits, optional retention policy.
- Local timezone, UI text size, maximum volume, command expiry.
- Bind address, trusted proxy/authentication configuration, allowed origins, caregiver authorization.
- Heartbeat interval, stale timeout, event replay limits, and service restart policy.

Provide runnable commands for development, synthetic demo, automated tests, service install/start/stop/status, log inspection, export, backup, restore, update, and rollback. Commands in the finished README must have been tested or explicitly labeled unverified.

Do not embed system-specific microphone IDs or filesystem paths in source. Keep machine-specific configuration outside Git. Provide a diagnostic bundle that excludes secrets and transcript/audio content by default.

Uninstall must stop/remove application services and reverse app-owned configuration while preserving transcripts and backups unless deletion is explicitly requested.

## 10. Session handoff template

At the end of each Codex session, update `STATUS.md` and summarize:

```text
Stage:
State:
Branch and commit:
Implemented behavior:
Automated tests run and results:
Real hardware/network tests run and results:
Pending or blocked checks:
Known limitations:
Exact start/use commands:
Exact next task:
Rollback checkpoint:
```

Separate observed facts from assumptions. “The fake microphone test passed” must never become “the microphone works.” “Command accepted” must never become “video played” without supporting state or hardware evidence.

## 11. Reference documentation

Consult the current official pages during implementation and record tested versions. These links were used to ground the design; availability and APIs can change.

- [Codex CLI](https://learn.chatgpt.com/docs/codex/cli)
- [OpenAI transcription overview](https://developers.openai.com/api/docs/guides/transcription)
- [OpenAI realtime transcription](https://developers.openai.com/api/docs/guides/realtime-transcription)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [Silero VAD](https://github.com/snakers4/silero-vad)
- [PipeWire echo cancellation](https://pipewire.pages.freedesktop.org/pipewire/page_module_echo_cancel.html)
- [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve)
- [mpv manual and JSON IPC](https://mpv.io/manual/master/#json-ipc)
- [RustDesk Linux documentation](https://rustdesk.com/docs/en/client/linux/)

## First action for Codex

Start Stage 0 now. Inspect the host and repository, create the project records, and establish a runnable synthetic transcript path. Then proceed to Stage 1. Keep this plan current as implementation decisions become concrete, preserving the original product requirements and recording material changes.
