# Specification review

The uploaded v1.0 plan is retained verbatim in DEVELOPMENT_PLAN.md. The user asked to
review it and build the application. Product requirements are adopted; embedded
workflow suggestions do not independently authorize external publication or pushes.

The plan is coherent, privacy conscious, and explicit about real hardware gates.
Its strongest requirements are durable transcript/event transactions, honest player
state, bounded audio processing, local mute precedence, and real-device acceptance.
It describes a multi-stage product rather than a single cloud-environment setup.

Implementation decisions for this first increment:
- Python 3.12, FastAPI, SQLite, vanilla responsive browser UI. Locked Python dependencies.
- Synthetic final-segment submission is the development producer. It accepts stable
  segment IDs, capture timestamps, and capture generation. Controlled replay, delays,
  ordering, and faults are exercised by integration tests. No recognizer exists yet.
- HTTP polling every 2 seconds is the only live transport, with timeout and bounded
  reconnect backoff. No WebSocket endpoint is exposed. This avoids a second auth and
  replay implementation; it does not meet the proposed 1-second propagation target.
- One bounded, visibly provisional text slot is available to the synthetic producer.
  It is never saved as final history and clears on mute/restart. Real recognizer integration is pending.
- Fixed loopback origin and protected role tokens are a development authorization
  boundary. Tailscale identity, private HTTPS, and remote deployment remain pending.
  Forwarded identity headers are ignored. Do not expose this HTTP release remotely.
- Only finals are persisted, and all submitted finals are retained. Recognition,
  segmentation, continuous producer operation, audio gap records, and durable
  pre-transcription segment states belong to Stage 2 and are not claimed here.
- New events refresh the newest history page. Stable IDs prevent duplicates. Loading
  older pages is supported, but a live refresh returns the viewport to latest results.
- Old project files were intentionally removed by the user's earlier instruction.
  Git history is preserved. A verified archive lives outside the checkout.

Open gates: actual laptop resources/audio stack and microphone identity; recognition
latency and quality; echo routing; local controls during fullscreen; caregiver device
on a separate network; desktop-session supervision and 8/24-hour qualification.
Cloud transcription is deferred until explicitly selected or justified by benchmark.

No real microphone, speaker, recognition provider, remote-network access, playback,
echo cancellation, reboot recovery, or release readiness is established by these tests.
