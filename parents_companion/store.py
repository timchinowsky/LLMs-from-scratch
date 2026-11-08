import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: Path):
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        if self.db.execute("PRAGMA user_version").fetchone()[0] > 1:
            self.db.close()
            raise ValueError("Database schema is newer than this application")
        self.db.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS transcripts(
            id TEXT PRIMARY KEY, capture_start TEXT NOT NULL, capture_end TEXT NOT NULL,
            finalized_at TEXT NOT NULL, text TEXT NOT NULL, backend TEXT NOT NULL,
            model TEXT NOT NULL, session_id TEXT NOT NULL, microphone TEXT NOT NULL,
            state TEXT NOT NULL, caregiver_status TEXT NOT NULL DEFAULT 'unread');
        CREATE TABLE IF NOT EXISTS events(
            seq INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, payload TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS capture_order ON transcripts(capture_start DESC, id DESC);
        PRAGMA user_version=1;
        """)
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO meta VALUES('instance', ?)", (str(uuid.uuid4()),)
            )
            self.db.execute("INSERT OR IGNORE INTO meta VALUES('muted', 'false')")
            self.db.execute("INSERT OR IGNORE INTO meta VALUES('generation', '0')")

    def close(self):
        self.db.close()

    def meta(self, key):
        with self.lock:
            return self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()[0]

    def event(self, kind, payload):
        self.db.execute("INSERT INTO events(kind,payload) VALUES(?,?)", (kind, json.dumps(payload)))

    def set_mute(self, muted):
        with self.lock, self.db:
            self.db.execute("UPDATE meta SET value=? WHERE key='muted'", (json.dumps(muted),))
            generation = int(self.meta("generation")) + 1
            self.db.execute("UPDATE meta SET value=? WHERE key='generation'", (str(generation),))
            self.event("listening", {"muted": muted, "generation": generation})

    def finalize(self, segment, generation):
        with self.lock, self.db:
            if self.meta("muted") == "true" or int(self.meta("generation")) != generation:
                return False
            existing = self.db.execute(
                "SELECT * FROM transcripts WHERE id=?", (segment["id"],)
            ).fetchone()
            if existing:
                if existing["text"] != segment["text"]:
                    raise ValueError("Segment ID already finalized with different text")
                return False
            row = {
                **segment,
                "finalized_at": now(),
                "backend": "synthetic",
                "model": "fixture-v1",
                "microphone": "synthetic-no-device",
                "state": "final",
                "caregiver_status": "unread",
            }
            names = ",".join(row)
            placeholders = ",".join("?" for _ in row)
            self.db.execute(
                f"INSERT INTO transcripts({names}) VALUES({placeholders})", tuple(row.values())
            )
            self.event("transcript", row)
            return True

    def acknowledge(self, segment_id, status):
        with self.lock, self.db:
            result = self.db.execute(
                "UPDATE transcripts SET caregiver_status=? WHERE id=?", (status, segment_id)
            )
            if result.rowcount == 0:
                return False
            self.event("acknowledgement", {"id": segment_id, "caregiver_status": status})
            return True

    def snapshot(self, query="", before=None, limit=50):
        with self.lock:
            # Snapshot rows and cursor under one lock, preventing a subscribe gap.
            cursor = self.db.execute("SELECT COALESCE(MAX(seq),0) FROM events").fetchone()[0]
            where = ["instr(lower(text), lower(?)) > 0"]
            args = [query]
            if before:
                where.append("(capture_start,id) < (?,?)")
                args.extend(before)
            rows = self.db.execute(
                "SELECT * FROM transcripts WHERE "
                + " AND ".join(where)
                + " ORDER BY capture_start DESC,id DESC LIMIT ?",
                [*args, limit + 1],
            ).fetchall()
            more = len(rows) > limit
            rows = [dict(row) for row in rows[:limit]]
            return {
                "items": rows,
                "instance": self.meta("instance"),
                "cursor": cursor,
                "next": [rows[-1]["capture_start"], rows[-1]["id"]] if more else None,
            }

    def replay(self, instance, after, limit=100):
        with self.lock:
            maximum = self.db.execute("SELECT COALESCE(MAX(seq),0) FROM events").fetchone()[0]
            minimum = self.db.execute("SELECT COALESCE(MIN(seq),0) FROM events").fetchone()[0]
            if instance != self.meta("instance") or after > maximum or after < max(0, minimum - 1):
                return None
            rows = self.db.execute(
                "SELECT * FROM events WHERE seq>? ORDER BY seq LIMIT ?", (after, limit)
            ).fetchall()
            return {
                "instance": instance,
                "events": [
                    {"seq": r["seq"], "kind": r["kind"], "payload": json.loads(r["payload"])}
                    for r in rows
                ],
                "cursor": rows[-1]["seq"] if rows else after,
                "more": bool(rows and rows[-1]["seq"] < maximum),
            }

    def backup(self, destination):
        with self.lock, sqlite3.connect(destination) as target:
            self.db.backup(target)
            # A restored backup must never share the old browser cursor namespace.
            target.execute("UPDATE meta SET value=? WHERE key='instance'", (str(uuid.uuid4()),))
