# Architecture, version 0.1

One loopback FastAPI process owns SQLite writes. Synchronous handlers run outside the
HTTP event loop; a reentrant lock serializes one shared connection. WAL mode and a
single transaction commit each final transcript or acknowledgement with its durable
event. Schema version 1 is created on first launch. No migration beyond v1 exists yet.

A local authenticated synthetic producer submits POST /api/synthetic/segments. Required
UUIDs and timezone-aware capture times are validated; timestamps normalize to UTC.
Capture order is independent of completion order. Same-ID repeats are idempotent;
changed final text is rejected. Local mute increments a persistent generation, so
muted and old-generation results are discarded even after unmute or restart.

GET /api/transcripts returns newest-first history, a database instance UUID, and an
atomic event cursor. Search is literal substring search, with at most 100 records per
page. Opaque JSON keyset cursors use capture time and ID. GET /api/events replays at
most 100 durable events per request. A different instance, future cursor, or a cursor
older than retained events returns 409/resync. Events currently have no automatic
retention. The browser refreshes an authoritative newest-page snapshot after an event;
rows use stable IDs. No WS endpoint is implemented. A single in-memory provisional slot is surfaced by status;
it is never authoritative history and clears on mute/restart.

Sessions use random eight-hour HttpOnly SameSite=Strict cookies, protected local role
tokens, origin validation, CSRF headers, and host validation. Sessions do not survive
server restart; sign in again. Role tokens survive restart in a mode-0600 file within
a mode-0700 state directory. Login attempts are rate limited. Proxy identity headers
are ignored. This is loopback development HTTP, not deployment authentication.

POST /api/session signs in; GET/DELETE /api/session inspect/end the session.
GET /api/status reports synthetic, local mute, disk health, and absent audio/player.
PATCH /api/transcripts/{uuid} sets unread/acknowledged/handled.
POST /api/local/listening is local-role-only; caregivers cannot unmute.
GET /api/export produces NDJSON. All state API routes require a session.

Static assets ship with the package; no external scripts, fonts, analytics, or CDNs.
CSP disallows inline scripts and framing. Transcript text uses textContent.
No media, shell commands, URL fetcher, audio queue, worker, or provider is implemented.
Storage failures latch a visible fault until restart; no success is returned for failed
writes. Existing history remains readable where possible. No automatic history deletion.
