"""FastAPI routes for Agent Studio and SSE event observation."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from x2video.application import ApplicationService
from x2video.auth.oauth import get_status
from x2video.config.loader import load_config
from x2video.util import discover_browser_executable


def _studio_config():
    try:
        return load_config()
    except Exception:
        return None


class CreateRunRequest(BaseModel):
    query: str
    autonomy: str = "assisted"
    target_duration_seconds: int = 60
    preferred_format: str | None = None
    mode: str | None = None


class StartRequest(BaseModel):
    background: bool = True


class ActionRequest(BaseModel):
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)


class FeedbackRequest(BaseModel):
    category: str = "preference"
    comment: str
    rating: int | None = Field(default=None, ge=1, le=5)
    target_id: str | None = None


class MemoryStatusRequest(BaseModel):
    status: str


def create_app(
    *,
    work_dir: str | None = None,
    db_path: str | None = None,
    config=None,
) -> FastAPI:
    resolved_work = work_dir or os.environ.get("X2VIDEO_WORK_DIR", "work")
    service = ApplicationService(work_dir=resolved_work, db_path=db_path, config=config)
    app = FastAPI(title="X2Video Agent Studio API", version="0.2.0")
    app.state.service = service

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        browser_path = discover_browser_executable()
        auth = get_status()
        live_ready = service.live_ready()
        checks = {
            "sqlite": Path(service.db_path).exists(),
            "ffmpeg": bool(shutil.which("ffmpeg") and shutil.which("ffprobe")),
            "browser": bool(browser_path and browser_path.exists()),
            "studio": (Path(__file__).resolve().parent / "static" / "index.html").exists(),
            "source": live_ready,
        }
        return {
            "ok": all(value for key, value in checks.items() if key != "source"),
            "version": "0.2.0",
            "mode": "live" if live_ready else "demo",
            "database": str(service.db_path),
            "checks": checks,
            "live_ready": live_ready,
            "source_provider": getattr(getattr(service.config, "source", None), "provider", None),
            "auth_logged_in": bool(auth.get("logged_in")),
        }

    @app.get("/api/runs")
    def list_runs() -> dict[str, Any]:
        return {"items": service.list_runs()}

    @app.post("/api/runs", status_code=201)
    def create_run(request: CreateRunRequest) -> dict[str, Any]:
        try:
            return service.create_run(**request.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        snapshot = service.get_run(run_id)
        if not snapshot:
            raise HTTPException(status_code=404, detail="Run not found")
        return snapshot

    @app.post("/api/runs/{run_id}/start")
    async def start_run(run_id: str, request: StartRequest) -> dict[str, Any]:
        if not service.get_run(run_id):
            raise HTTPException(status_code=404, detail="Run not found")
        if request.background:
            return {"run_id": run_id, "worker_pid": service.start_worker(run_id)}
        await service.execute(run_id)
        return service.get_run(run_id) or {}

    @app.post("/api/runs/{run_id}/actions")
    def run_action(run_id: str, request: ActionRequest) -> dict[str, Any]:
        try:
            return service.action(run_id, request.action, request.payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/runs/{run_id}/feedback", status_code=201)
    def feedback(run_id: str, request: FeedbackRequest) -> dict[str, Any]:
        try:
            return service.feedback(run_id, **request.model_dump())
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/memories")
    def memories(status: str | None = None) -> dict[str, Any]:
        return {"items": service.store.list_memories(status=status)}

    @app.post("/api/memories/{memory_id}")
    def memory_status(memory_id: str, request: MemoryStatusRequest) -> dict[str, Any]:
        try:
            return service.store.set_memory_status(memory_id, request.status)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/runs/{run_id}/replay")
    def replay(run_id: str) -> dict[str, Any]:
        try:
            return service.runtime.replay(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/runs/{run_id}/events")
    async def events(run_id: str) -> StreamingResponse:
        if not service.get_run(run_id):
            raise HTTPException(status_code=404, detail="Run not found")

        async def stream():
            cursor = None
            while True:
                items = service.store.list_events(run_id, after=cursor)
                for item in items:
                    cursor = item["created_at"]
                    yield f"event: run_event\ndata: {json.dumps(item, ensure_ascii=False)}\n\n"
                run = service.store.get_run(run_id)
                if run and run["state"] in {"COMPLETE", "FAILED", "CANCELED"}:
                    yield "event: stream_end\ndata: {}\n\n"
                    return
                await asyncio.sleep(0.4)

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.get("/api/runs/{run_id}/media/{kind}")
    def media(run_id: str, kind: str) -> FileResponse:
        names = {"video": "video.mp4", "cover": "cover.png"}
        if kind not in names:
            raise HTTPException(status_code=404, detail="Media not found")
        path = Path(service.work_dir) / "agent_runs" / run_id / "publish_kit" / names[kind]
        if not path.exists():
            raise HTTPException(status_code=404, detail="Media not found")
        return FileResponse(path)

    dist = Path(__file__).resolve().parent / "static"
    if dist.exists():
        assets = dist / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=assets), name="studio-assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def studio_shell(full_path: str) -> FileResponse:
            candidate = (dist / full_path).resolve()
            if candidate.is_relative_to(dist.resolve()) and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(dist / "index.html")
    return app


app = create_app(config=_studio_config())
