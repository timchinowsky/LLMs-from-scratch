from datetime import datetime, timezone, timedelta
import json
import sqlite3
import uuid

from fastapi.testclient import TestClient
import pytest

from parents_companion.app import create_app
from parents_companion.config import Settings
from parents_companion.store import Store

ORIGIN = "http://127.0.0.1:8765"


@pytest.fixture
def app(tmp_path):
    return create_app(Settings(data_dir=tmp_path))


@pytest.fixture
def client(app):
    with TestClient(app, base_url=ORIGIN) as client:
        token = app.state.credentials["local"]
        result = client.post("/api/session", json={"token": token}, headers={"Origin": ORIGIN})
        client.headers.update({"Origin": ORIGIN, "X-CSRF-Token": result.json()["csrf"]})
        yield client


def segment(text="Could you turn down the music?", minutes=0, generation=0):
    start = datetime(2026, 11, 1, 9, tzinfo=timezone.utc) + timedelta(minutes=minutes)
    return {
        "id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4()),
        "text": text,
        "capture_start": start.isoformat(),
        "capture_end": (start + timedelta(seconds=3)).isoformat(),
        "generation": generation,
    }


def test_durable_out_of_order_and_duplicate(client, app):
    later, earlier = segment(minutes=1), segment()
    assert client.post("/api/synthetic/segments", json=later).json()["saved"]
    assert client.post("/api/synthetic/segments", json=earlier).json()["saved"]
    assert not client.post("/api/synthetic/segments", json=earlier).json()["saved"]
    changed = {**earlier, "text": "different"}
    assert client.post("/api/synthetic/segments", json=changed).status_code == 409
    result = client.get("/api/transcripts").json()
    assert [r["id"] for r in result["items"]] == [later["id"], earlier["id"]]
    separate = Store(app.state.settings.data_dir / "companion.sqlite3")
    assert len(separate.snapshot()["items"]) == 2
    separate.close()


def test_snapshot_replay_race_and_resync(client):
    snapshot = client.get("/api/transcripts").json()
    item = segment()
    client.post("/api/synthetic/segments", json=item)
    params = {"instance": snapshot["instance"], "after": snapshot["cursor"]}
    replay = client.get("/api/events", params=params).json()
    assert [e["payload"]["id"] for e in replay["events"]] == [item["id"]]
    assert client.get("/api/events", params=params).json() == replay
    params["after"] = replay["cursor"]
    assert client.get("/api/events", params=params).json()["events"] == []
    params["instance"] = "old-database"
    assert client.get("/api/events", params=params).status_code == 409
    params["instance"] = snapshot["instance"]
    params["after"] = 999
    assert client.get("/api/events", params=params).status_code == 409


def test_mute_survives_restart_and_cancels_late_results(client, app):
    assert client.post("/api/local/listening", json={"muted": True}).status_code == 200
    assert not client.post("/api/synthetic/segments", json=segment()).json()["saved"]
    separate = Store(app.state.settings.data_dir / "companion.sqlite3")
    assert separate.meta("muted") == "true"
    separate.close()
    client.post("/api/local/listening", json={"muted": False})
    assert not client.post("/api/synthetic/segments", json=segment()).json()["saved"]
    generation = client.get("/api/status").json()["generation"]
    assert client.post("/api/synthetic/segments", json=segment(generation=generation)).json()[
        "saved"
    ]


def test_pagination_search_and_ack(client):
    for index in range(5):
        client.post(
            "/api/synthetic/segments", json=segment("Hello 世界 <script>alert(1)</script>", index)
        )
    seen = []
    before = None
    for _ in range(3):
        params = {"limit": 2, "q": "世界"}
        if before:
            params["before"] = json.dumps(before)
        result = client.get("/api/transcripts", params=params).json()
        seen.extend(row["id"] for row in result["items"])
        before = result["next"]
    assert len(set(seen)) == len(seen) == 5
    assert before is None
    assert client.get("/api/transcripts", params={"q": "missing"}).json()["items"] == []
    assert (
        client.patch("/api/transcripts/" + seen[0], json={"status": "handled"}).status_code == 200
    )
    assert client.get("/api/transcripts").json()["items"][0]["caregiver_status"] == "handled"
    assert client.get("/api/transcripts", params={"before": '["bad"]'}).status_code == 422
    assert client.get("/api/transcripts", params={"limit": 1000}).status_code == 422


def test_authorization_csrf_and_local_boundary(client, app):
    with TestClient(create_app(app.state.settings), base_url=ORIGIN) as stranger:
        assert stranger.get("/api/transcripts").status_code == 401
        assert (
            stranger.get("/api/status", headers={"Tailscale-User-Login": "caregiver"}).status_code
            == 401
        )
        assert stranger.get("/api/events", params={"instance": "x", "after": 0}).status_code == 401
        assert stranger.post("/api/session", json={"token": "x" * 20}).status_code == 403
        assert stranger.get("/", headers={"Host": "evil.example"}).status_code == 400
        result = stranger.post(
            "/api/session",
            json={"token": app.state.credentials["caregiver"]},
            headers={"Origin": ORIGIN},
        )
        headers = {"Origin": ORIGIN, "X-CSRF-Token": result.json()["csrf"]}
        assert (
            stranger.post(
                "/api/local/listening", json={"muted": False}, headers=headers
            ).status_code
            == 403
        )
        assert (
            stranger.post("/api/synthetic/segments", json=segment(), headers=headers).status_code
            == 403
        )
    assert (
        client.post(
            "/api/local/listening", json={"muted": True}, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/local/listening", json={"muted": True}, headers={"X-CSRF-Token": "wrong"}
        ).status_code
        == 403
    )
    assert (
        client.get("/api/session").headers["content-security-policy"].find("frame-ancestors 'none'")
        >= 0
    )


def test_invalid_and_partial_results_are_not_persisted(client):
    bad = segment()
    bad["capture_end"] = "2020-01-01T00:00:00+00:00"
    assert client.post("/api/synthetic/segments", json=bad).status_code == 422
    bad = segment()
    bad["capture_start"] = "2026-01-01T00:00:00"
    assert client.post("/api/synthetic/segments", json=bad).status_code == 422
    assert client.post("/api/synthetic/partial", json={"text": "provisional"}).status_code == 422
    assert client.get("/api/transcripts").json()["items"] == []


def test_backup_restore_and_export(client, app, tmp_path):
    client.post("/api/synthetic/segments", json=segment("A fictional backup entry"))
    assert "A fictional backup entry" in client.get("/api/export").text
    target = tmp_path / "backup.sqlite3"
    app.state.store.backup(target)
    backup = Store(target)
    assert backup.meta("instance") != app.state.store.meta("instance")
    assert backup.snapshot()["items"][0]["text"] == "A fictional backup entry"
    assert backup.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    backup.close()


def test_storage_fault_is_visible(client, app, monkeypatch):
    import parents_companion.app as module

    monkeypatch.setattr(module.shutil, "disk_usage", lambda _: type("Disk", (), {"free": 0})())
    assert client.get("/api/status").json()["storage"] == "fault"
    assert client.post("/api/synthetic/segments", json=segment()).status_code == 503
    assert client.get("/api/transcripts").json()["items"] == []


def test_db_failure_is_not_reported_as_saved(client, app, monkeypatch):
    def fail(*_):
        raise sqlite3.OperationalError("synthetic storage failure")

    monkeypatch.setattr(app.state.store, "finalize", fail)
    assert client.post("/api/synthetic/segments", json=segment()).status_code == 503
    assert client.get("/api/status").json()["storage"] == "fault"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"synthetic": False},
        {"min_free_mb": -1},
        {"timezone": "not-a-zone"},
        {"origin": "http://0.0.0.0"},
    ],
)
def test_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        Settings(**kwargs)


def test_event_replay_is_bounded_and_pruned_cursor_resyncs(client, app):
    snap = client.get("/api/transcripts").json()
    for i in range(105):
        client.post("/api/synthetic/segments", json=segment(minutes=i))
    result = client.get("/api/events", params={"instance": snap["instance"], "after": 0}).json()
    assert len(result["events"]) == 100 and result["more"]
    with app.state.store.db:
        app.state.store.db.execute("DELETE FROM events WHERE seq < 50")
    assert (
        client.get("/api/events", params={"instance": snap["instance"], "after": 0}).status_code
        == 409
    )


def test_provisional_is_ephemeral_and_mute_clears_it(client):
    item = segment()
    partial = {"id": item["id"], "text": "A provisional phrase", "generation": 0}
    assert client.post("/api/synthetic/partial", json=partial).json()["accepted"]
    assert client.get("/api/status").json()["partial"]["text"] == partial["text"]
    assert client.get("/api/transcripts").json()["items"] == []
    client.post("/api/local/listening", json={"muted": True})
    assert client.get("/api/status").json()["partial"] is None
    assert not client.post("/api/synthetic/partial", json=partial).json()["accepted"]


def test_restart_keeps_finals_but_discards_sessions_and_partials(tmp_path):
    settings = Settings(data_dir=tmp_path)
    with TestClient(create_app(settings), base_url=ORIGIN) as first:
        credentials = json.loads((tmp_path / "credentials.json").read_text())
        login = first.post(
            "/api/session", json={"token": credentials["local"]}, headers={"Origin": ORIGIN}
        ).json()
        first.headers.update({"Origin": ORIGIN, "X-CSRF-Token": login["csrf"]})
        assert first.post("/api/synthetic/segments", json=segment()).json()["saved"]
        cookies = dict(first.cookies)
    with TestClient(create_app(settings), base_url=ORIGIN) as second:
        second.cookies.update(cookies)
        assert second.get("/api/transcripts").status_code == 401
        second.post(
            "/api/session", json={"token": credentials["local"]}, headers={"Origin": ORIGIN}
        )
        assert len(second.get("/api/transcripts").json()["items"]) == 1
        assert second.get("/api/status").json()["partial"] is None
