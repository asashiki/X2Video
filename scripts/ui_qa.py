"""Run the real API and Studio, create a Demo Run, and capture QA screenshots."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import time
from datetime import date
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright


def wait_http(url: str, timeout: float = 20) -> None:
    deadline = time.time() + timeout
    with httpx.Client(trust_env=False) as client:
        while time.time() < deadline:
            try:
                if client.get(url).status_code < 500:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.2)
    raise RuntimeError(f"Timed out waiting for {url}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chromium", required=True)
    parser.add_argument("--output", default=f"artifacts/ui-qa/{date.today().isoformat()}")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    output = root / args.output
    output.mkdir(parents=True, exist_ok=True)
    qa_work = root / "work" / "ui-qa" / date.today().isoformat()
    qa_work.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ)
    environment["X2VIDEO_WORK_DIR"] = str(qa_work)
    environment["X2VIDEO_BROWSER_EXECUTABLE"] = str(Path(args.chromium).resolve())
    api = subprocess.Popen(
        [
            str(root / ".venv" / "bin" / "uvicorn"),
            "x2video.api.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8765",
        ],
        cwd=root,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    vite = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=root / "studio",
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        wait_http("http://127.0.0.1:8765/api/health")
        wait_http("http://127.0.0.1:5173")
        with httpx.Client(base_url="http://127.0.0.1:8765", trust_env=False, timeout=30) as client:
            created = client.post(
                "/api/runs",
                json={
                    "query": "帮我做一条60秒以内、给普通中文用户看的今日AI圈三件事。避免重复，优先可信消息。",
                    "autonomy": "auto",
                    "target_duration_seconds": 60,
                },
            )
            created.raise_for_status()
            run_id = created.json()["run"]["run_id"]
            completed = client.post(f"/api/runs/{run_id}/start", json={"background": False})
            completed.raise_for_status()

        routes = {
            "dashboard": "/",
            "new-run": "/new",
            "timeline": f"/runs/{run_id}?view=timeline",
            "curation": f"/runs/{run_id}?view=curation",
            "script": f"/runs/{run_id}?view=script",
            "qc": f"/runs/{run_id}?view=qc",
            "memory": "/memory",
            "settings": "/settings",
        }
        with sync_playwright() as playwright:
            for label, viewport in (("desktop", {"width": 1440, "height": 1000}), ("mobile", {"width": 390, "height": 844})):
                # The portable Lambda Chromium build is single-process. A fresh browser
                # per viewport avoids a process teardown when the first context closes.
                browser = playwright.chromium.launch(
                    executable_path=args.chromium,
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--single-process",
                        "--use-angle=swiftshader",
                        "--enable-unsafe-swiftshader",
                    ],
                )
                context = browser.new_context(viewport=viewport, device_scale_factor=1)
                page = context.new_page()
                for name, route in routes.items():
                    page.goto(f"http://127.0.0.1:5173{route}", wait_until="networkidle")
                    page.evaluate("document.fonts.ready")
                    page.screenshot(path=output / f"{label}-{name}.png", full_page=False)
                context.close()
                browser.close()
        print(f"run_id={run_id}")
        print(f"screenshots={output}")
    finally:
        for process in (vite, api):
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
        for process in (vite, api):
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)


if __name__ == "__main__":
    main()
