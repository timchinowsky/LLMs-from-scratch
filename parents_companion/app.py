from contextlib import asynccontextmanager
from datetime import datetime
import json
import os
from pathlib import Path
import secrets
import shutil
import sqlite3
import time
import uuid
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from .config import Settings
from .store import Store

STATIC = Path(__file__).parent / "static"


class Login(BaseModel):
    token: str = Field(min_length=16, max_length=200)


class Mute(BaseModel):
    muted: bool


class Acknowledgement(BaseModel):
    status: Literal["unread", "acknowledged", "handled"]


class Partial(BaseModel):
    id: uuid.UUID
    text: str = Field(min_length=1, max_length=20000)
    generation: int = Field(ge=0)


class Segment(BaseModel):
    id: uuid.UUID
    capture_start: datetime
    capture_end: datetime
    text: str = Field(min_length=1, max_length=20000)
    session_id: uuid.UUID
    generation: int = Field(ge=0)

    @field_validator("capture_start", "capture_end")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError("Capture timestamps require timezone information")
        return value


def create_app(settings=None):
    settings = settings or Settings()
    sessions = {}
    login_attempts = {}
    state = {"storage_fault": False, "partial": None}

    @asynccontextmanager
    async def lifespan(app):
        settings.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(settings.data_dir, 0o700)
        credentials_path = settings.data_dir / "credentials.json"
        if not credentials_path.exists():
            fd = os.open(credentials_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as file:
                json.dump(
                    {role: secrets.token_urlsafe(32) for role in ("caregiver", "local")}, file
                )
        os.chmod(credentials_path, 0o600)
        app.state.credentials = json.loads(credentials_path.read_text())
        app.state.store = Store(settings.data_dir / "companion.sqlite3")
        app.state.settings = settings
        try:
            yield
        finally:
            app.state.store.close()
            sessions.clear()

    app = FastAPI(
        title="Parents Companion",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.middleware("http")
    async def security(request: Request, call_next):
        if request.headers.get("host") not in ("127.0.0.1:8765",):
            return JSONResponse({"detail": "Unapproved host"}, status_code=400)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if request.headers.get("origin") != settings.origin:
                return JSONResponse({"detail": "Unapproved origin"}, status_code=403)
        try:
            response = await call_next(request)
        except (sqlite3.Error, OSError):
            state["storage_fault"] = True
            return JSONResponse(
                {"detail": "Storage fault; transcripts are not being saved"}, status_code=503
            )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    def authorized(request: Request):
        sid = request.cookies.get("companion_session", "")
        session = sessions.get(sid)
        if not session or session["expires"] < time.monotonic():
            sessions.pop(sid, None)
            raise HTTPException(401, "Sign in to continue")
        if request.method not in ("GET", "HEAD"):
            if not secrets.compare_digest(request.headers.get("x-csrf-token", ""), session["csrf"]):
                raise HTTPException(403, "Invalid CSRF token")
        return session

    def local(session=Depends(authorized)):
        if session["role"] != "local":
            raise HTTPException(403, "This control requires the local parent session")
        return session

    def check_disk():
        low = shutil.disk_usage(settings.data_dir).free < settings.min_free_mb * 1024 * 1024
        if low or state["storage_fault"]:
            raise HTTPException(503, "Storage fault; transcripts are not being saved")

    @app.get("/")
    @app.get("/local")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/static/{name}")
    def static(name: Literal["app.js", "style.css"]):
        return FileResponse(STATIC / name)

    @app.post("/api/session")
    def login(body: Login, request: Request, response: Response):
        address = request.client.host if request.client else "unknown"
        current = time.monotonic()
        attempts = [t for t in login_attempts.get(address, []) if current - t < 60]
        if len(attempts) >= 10:
            raise HTTPException(429, "Too many sign-in attempts; wait one minute")
        login_attempts[address] = [*attempts, current]
        role = next(
            (
                role
                for role, token in app.state.credentials.items()
                if secrets.compare_digest(body.token, token)
            ),
            None,
        )
        if role is None:
            raise HTTPException(401, "Invalid access token")
        if len(sessions) >= 100:
            sessions.clear()
        sid, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        sessions[sid] = {"role": role, "csrf": csrf, "expires": current + 8 * 3600}
        response.set_cookie(
            "companion_session", sid, httponly=True, samesite="strict", max_age=8 * 3600, path="/"
        )
        return {"role": role, "csrf": csrf}

    @app.get("/api/session")
    def session_info(session=Depends(authorized)):
        return {"role": session["role"], "csrf": session["csrf"]}

    @app.delete("/api/session")
    def logout(request: Request, response: Response, session=Depends(authorized)):
        sessions.pop(request.cookies.get("companion_session"), None)
        response.delete_cookie("companion_session")
        return {"signed_out": True}

    @app.get("/api/status")
    def status(session=Depends(authorized)):
        free = shutil.disk_usage(settings.data_dir).free
        healthy = free >= settings.min_free_mb * 1024 * 1024 and not state["storage_fault"]
        return {
            "mode": "synthetic",
            "audio_leaves_laptop": False,
            "microphone": "Not connected — synthetic data only",
            "worker": "not configured",
            "muted": app.state.store.meta("muted") == "true",
            "generation": int(app.state.store.meta("generation")),
            "backlog": 0,
            "storage": "ok" if healthy else "fault",
            "disk_free_mb": free // (1024 * 1024),
            "player": "not configured",
            "timezone": settings.timezone,
            "version": "0.1.0",
            "partial": state["partial"],
        }

    @app.post("/api/local/listening")
    def listening(body: Mute, session=Depends(local)):
        check_disk()
        app.state.store.set_mute(body.muted)
        state["partial"] = None
        return {"muted": body.muted}

    @app.post("/api/synthetic/partial")
    def partial(body: Partial, session=Depends(local)):
        if app.state.store.meta("muted") == "true" or body.generation != int(
            app.state.store.meta("generation")
        ):
            return {"accepted": False}
        state["partial"] = {"id": str(body.id), "text": body.text}
        return {"accepted": True}

    @app.post("/api/synthetic/segments")
    def synthetic(body: Segment, session=Depends(local)):
        check_disk()
        if body.capture_end < body.capture_start:
            raise HTTPException(422, "capture_end precedes capture_start")
        from datetime import timezone

        segment = {
            "id": str(body.id),
            "session_id": str(body.session_id),
            "text": body.text,
            "capture_start": body.capture_start.astimezone(timezone.utc).isoformat(),
            "capture_end": body.capture_end.astimezone(timezone.utc).isoformat(),
        }
        try:
            saved = app.state.store.finalize(segment, body.generation)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None
        if state["partial"] and state["partial"]["id"] == segment["id"]:
            state["partial"] = None
        return {"saved": saved, "id": segment["id"]}

    @app.get("/api/transcripts")
    def transcripts(
        q: str = Query("", max_length=200),
        before: str | None = None,
        limit: int = Query(50, ge=1, le=100),
        session=Depends(authorized),
    ):
        cursor = None
        if before:
            try:
                cursor = json.loads(before)
                if not isinstance(cursor, list) or len(cursor) != 2:
                    raise ValueError()
                datetime.fromisoformat(cursor[0])
                uuid.UUID(cursor[1])
            except (ValueError, TypeError, json.JSONDecodeError):
                raise HTTPException(422, "Invalid history cursor") from None
        return app.state.store.snapshot(q, cursor, limit)

    @app.patch("/api/transcripts/{segment_id}")
    def acknowledge(segment_id: uuid.UUID, body: Acknowledgement, session=Depends(authorized)):
        check_disk()
        if not app.state.store.acknowledge(str(segment_id), body.status):
            raise HTTPException(404, "Transcript not found")
        return {"status": body.status}

    @app.get("/api/events")
    def events(instance: str, after: int = Query(ge=0), session=Depends(authorized)):
        result = app.state.store.replay(instance, after)
        if result is None:
            return JSONResponse({"resync": True}, status_code=409)
        return result

    @app.get("/api/export")
    def export(session=Depends(authorized)):
        def records():
            # Independent read snapshot; export never locks the shared writer or buffers all history.
            connection = sqlite3.connect(settings.data_dir / "companion.sqlite3")
            connection.row_factory = sqlite3.Row
            try:
                cursor = connection.execute("SELECT * FROM transcripts ORDER BY capture_start,id")
                for row in cursor:
                    yield json.dumps(dict(row), ensure_ascii=False) + "\n"
            finally:
                connection.close()

        return StreamingResponse(
            records(),
            media_type="application/x-ndjson",
            headers={"Content-Disposition": "attachment; filename=transcripts.ndjson"},
        )

    return app
